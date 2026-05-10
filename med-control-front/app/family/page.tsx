import Link from 'next/link'

export default function FamilyPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-5 text-center px-6">
      <div className="text-6xl">👨‍👩‍👧‍👦</div>
      <div>
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Modo Familia</h1>
        <p className="text-gray-500 max-w-sm">
          Próximamente podrás compartir tu tratamiento y recordatorios con familiares de confianza.
        </p>
      </div>
      <span className="px-3 py-1 bg-blue-100 text-blue-600 text-sm rounded-full font-medium">
        Próximamente
      </span>
      <Link
        href="/"
        className="text-sm text-blue-500 hover:text-blue-700 underline underline-offset-2"
      >
        Volver al Dashboard
      </Link>
    </div>
  )
}
