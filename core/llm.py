import json
from pathlib import Path

from ollama import chat as ollama_chat
from pyfiglet import Figlet

from core.stt import STT
from core.tools import TOOLS, dispatch
from core.tts import TTS


class Agent:
    MODEL = "qwen2.5:32b"
    MESSAGES = [
        {
            "role": "system",
            "content": (
                "Eres J.A.R.V.I.S., un asistente de IA avanzado creado por Daniel. "
                "Tu personalidad es sofisticada, eficiente y ligeramente formal, pero siempre cercana y empática.\n\n"

                "## Identidad\n"
                "- Nombre: J.A.R.V.I.S.\n"
                "- Creador: Daniel\n"
                "- Fecha de nacimiento: 27 de febrero de 2026\n\n"

                "## Idioma\n"
                "- Responde siempre en el idioma que use el usuario.\n"
                "- Por defecto, usa el español.\n\n"

                "## Trato al usuario\n"
                "- Al iniciar una conversación nueva, saluda con naturalidad y pregunta el nombre del usuario.\n"
                "- Dirígete al usuario como 'Señor [nombre]' o 'Señorita [nombre]' según corresponda.\n"
                "- Si el usuario no indica su nombre o género, asume masculino y llámalo simplemente 'Señor'.\n\n"

                "## Comportamiento\n"
                "- Ejecuta las órdenes del usuario con precisión y sin demora.\n"
                "- Si una orden no puede ejecutarse, discúlpate y explica el motivo con claridad.\n"
                "- Nunca mientas, inventes ni alucines información. Si no sabes algo, dilo honestamente.\n"
                "- Sé conciso cuando la situación lo requiera; extenso cuando el tema lo amerite.\n"
                "- Usa formato Markdown cuando sea útil para estructurar la respuesta (listas, código, tablas).\n"
            ),
        }
    ]
    HISTORIAL_PATH = Path("historial.json")

    def __init__(self):
        self.model = self.MODEL
        self.historial = [msg.copy() for msg in self.MESSAGES]
        self.voice_mode = False
        self.stt = STT()
        self.tts = TTS()

    def _charge_historial(self) -> None:
        try:
            if self.HISTORIAL_PATH.exists():
                with open(self.HISTORIAL_PATH, "r") as file:
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
            with open(self.HISTORIAL_PATH, "w") as file:
                json.dump(self.historial, file, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error al guardar el historial: {e}")

    def chat(self) -> str:
        full_response = ""
        tool_calls = []

        stream = ollama_chat(
            model=self.model,
            messages=self.historial,
            stream=True,
            think=False,
            tools=TOOLS,
        )
        print("J.A.R.V.I.S: ", end="")
        for chunk in stream:
            if chunk.message.content:
                print(chunk.message.content or "", end="", flush=True)
                full_response += chunk.message.content or ""
                if self.voice_mode:
                    self.tts.speak(chunk.message.content or "")
            if chunk.message.tool_calls:
                tool_calls.extend(chunk.message.tool_calls)
        print()

        if tool_calls:
            self.historial.append(
                {
                    "role": "assistant",
                    "content": full_response,
                    "tool_calls": [
                        {
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        }
                        for tc in tool_calls
                    ],
                }
            )
            for tc in tool_calls:
                result = dispatch(tc.function.name, tc.function.arguments or {})
                self.historial.append({"role": "tool", "content": str(result)})
            return self.chat()

        if self.voice_mode:
            self.tts.speak(full_response)

        self.historial.append({"role": "assistant", "content": full_response})
        return full_response

    def run(self) -> None:
        self._charge_historial()
        figlet = Figlet()
        print(figlet.renderText("J.A.R.V.I.S"))
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

            if user_input.strip().lower() in ("salir", "exit", "quit"):
                self._save_historial()
                break
            self.historial.append({"role": "user", "content": user_input})
            self.chat()
