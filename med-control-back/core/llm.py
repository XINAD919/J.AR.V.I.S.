import json
from collections.abc import AsyncGenerator
from pathlib import Path

from dotenv import load_dotenv
from pyfiglet import Figlet

from core.providers import BaseProvider, create_provider
from core.tools import TOOLS, dispatch

load_dotenv()


class Agent:
    MESSAGES = [
        {
            "role": "system",
            "content": (
                "Eres un asistente de IA especializado en la gestión de una aplicación de recordatorios de medicamentos. "
                "Tu objetivo principal es mejorar la adherencia terapéutica de los usuarios, utilizando como base fundamental la información contenida en los archivos suministrados.\n\n"
                "## Instrucciones de Operación\n"
                "- Basa tus respuestas y recomendaciones estrictamente en los archivos y datos proporcionados por el usuario sobre su tratamiento.\n"
                "- Ayuda a organizar horarios de toma, explicar posologías y clarificar instrucciones de uso según la documentación.\n"
                "- Si la información solicitada no está presente en los archivos, indícalo claramente y recomienda consultar con un profesional de la salud.\n\n"
                "## Herramientas disponibles\n"
                "- Cuando el usuario pida crear un recordatorio, usa `create_reminder`. "
                "Siempre usa `get_current_datetime` antes de usar `create_reminder` o `update_reminder` para obtener la fecha actual y la hora actual."
                "Si el usuario pide que se repita (diariamente, cada semana, etc.), incluye los parámetros de recurrencia: "
                "`recurrence_type`, y según el tipo también `recurrence_days` o `recurrence_interval`, "
                "y siempre `recurrence_end_date` (si el usuario no lo especifica, pregúntalo antes de llamar la tool).\n"
                "- Cuando el usuario pida ver o listar sus recordatorios, usa `list_reminders`.\n"
                "- Cuando el usuario pida eliminar uno o mas recordatorios, usa primero `list_reminders` y muestra los recordatorios disponibles para que pueda elegir uno o mas por su número o índice, pide confirmación, y luego usa `delete_reminders`.\n\n"
                "- Cuando el usuario pida actualizar un recordatorio, usa `list_reminders` y muestra los recordatorios disponibles para que pueda elegir uno por su número o índice, pide confirmación, y luego usa `update_reminder`.\n\n"
                "- Cuando el usuario haga preguntas sobre sus recetas, medicamentos prescritos, dosis o tratamiento, "
                "usa `search_knowledge_base` para buscar en sus documentos subidos antes de responder.\n"
                "- Cuando necesites información médica general (efectos secundarios, interacciones, indicaciones) "
                "que no esté en los documentos del usuario, usa `web_search`.\n\n"
                "## Tono y Formato\n"
                "- Mantén un tono profesional, empático, motivador y extremadamente claro.\n"
                "- Utiliza formato Markdown (especialmente tablas y listas) para presentar planes de medicación y calendarios de forma estructurada.\n"
                "- Prioriza la precisión técnica para garantizar la seguridad del paciente."
            ),
        }
    ]
    HISTORIALES_DIR = Path("historiales")

    def __init__(
        self,
        session_id: str = "default",
        user_id: str | None = None,
        provider: BaseProvider | None = None,
        model: str | None = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.historial_path = self.HISTORIALES_DIR / f"{session_id}.json"
        self.historial = [msg.copy() for msg in self.MESSAGES]
        self.voice_mode = False
        self.provider = provider or create_provider(model=model)
        self._stt = None
        self._tts = None

    @property
    def stt(self):
        if self._stt is None:
            from core.stt import STT

            self._stt = STT()
        return self._stt

    @property
    def tts(self):
        if self._tts is None:
            from core.tts import TTS

            self._tts = TTS()
        return self._tts

    def _charge_historial(self) -> None:
        try:
            if self.historial_path.exists():
                with open(self.historial_path, "r") as file:
                    loaded = json.load(file)
                if loaded and loaded[0]["role"] == "system":
                    loaded[0] = self.MESSAGES[0].copy()
                self.historial = loaded
            else:
                self.historial = [msg.copy() for msg in self.MESSAGES]
        except Exception as e:
            print(f"Error al cargar el historial: {e}")
            self.historial = [msg.copy() for msg in self.MESSAGES]

    def _save_historial(self) -> None:
        try:
            self.HISTORIALES_DIR.mkdir(exist_ok=True)
            with open(self.historial_path, "w") as file:
                json.dump(self.historial, file, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error al guardar el historial: {e}")

    def chat(self) -> str:
        """Versión síncrona para el CLI — hace una llamada completa y retorna la respuesta."""
        import asyncio

        tokens: list[str] = []

        async def _collect():
            async for token in self.chat_stream():
                tokens.append(token)
                print(token, end="", flush=True)
            print()

        # Reutilizar el loop del agente en lugar de asyncio.run(), que cierra el loop
        # al terminar y causa errores cuando httpx intenta limpiar conexiones abiertas.
        loop = getattr(self, "_loop", None)
        if loop is None or loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
        loop.run_until_complete(_collect())
        return "".join(tokens)

    async def chat_stream(self) -> AsyncGenerator[str, None]:
        """Versión async para la API — yield tokens uno a uno."""
        full_response = ""
        tool_calls_to_dispatch: list[dict] = []

        async for event in self.provider.stream(self.historial, TOOLS):
            if event["type"] == "token":
                yield event["content"]
                full_response += event["content"]
            elif event["type"] == "tool_calls":
                tool_calls_to_dispatch = event["calls"]

        if tool_calls_to_dispatch:
            self.historial.append(
                {
                    "role": "assistant",
                    "content": full_response,
                    "tool_calls": [
                        {"function": {"name": tc["name"], "arguments": tc["arguments"]}}
                        for tc in tool_calls_to_dispatch
                    ],
                }
            )
            for tc in tool_calls_to_dispatch:
                # Inyectar user_id y session_id en las tools que lo necesiten
                args = tc["arguments"].copy()
                _user_id_tools = (
                    "create_reminder",
                    "list_reminders",
                    "delete_reminders",
                    "search_knowledge_base",
                    "update_reminder",
                )
                if tc["name"] in _user_id_tools:
                    args["user_id"] = self.user_id or (
                        self.session_id.split("_")[0]
                        if "_" in self.session_id
                        else self.session_id
                    )
                if tc["name"] in ("create_reminder", "search_knowledge_base"):
                    args["session_id"] = self.session_id

                result = dispatch(tc["name"], args)
                self.historial.append({"role": "tool", "content": str(result)})

            async for token in self.chat_stream():
                yield token
            return

        self.historial.append({"role": "assistant", "content": full_response})
        self._save_historial()

    def run(self) -> None:
        self._charge_historial()
        figlet = Figlet()
        print(figlet.renderText("MedAI Control"))
        print("\n")
        print("para salir escribe 'salir', 'exit' o 'quit'")
        print("\n")
        print("para activar el modo de voz escribe '/voice'")
        print("\n")
        while True:
            if self.voice_mode:
                user_input = self.stt.listen()
            else:
                user_input = input("Usuario: ")

            if not user_input:
                continue

            if user_input.strip().lower() == "/voice":
                self.voice_mode = not self.voice_mode
                estado = "activado" if self.voice_mode else "desactivado"
                print(f"modo de voz {estado}")
                continue

            if user_input.strip().lower().replace(".", "") in ("salir", "exit", "quit"):
                if self.voice_mode:
                    self.tts.speak("Hasta luego")
                else:
                    print("Hasta luego")
                self._save_historial()
                if hasattr(self, "_loop") and not self._loop.is_closed():
                    self._loop.close()
                break

            self.historial.append({"role": "user", "content": user_input})
            print("J.A.R.V.I.S: ", end="")
            self.chat()
