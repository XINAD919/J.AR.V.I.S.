import type { Session } from 'next-auth'

export type UserRole = 'USER' | 'CAREGIVER'

export function canWrite(session: Session | null): boolean {
  if (!session?.user?.role) return false
  return session.user.role !== 'CAREGIVER'
}

export function assertCanWrite(session: Session | null): void {
  if (!canWrite(session)) {
    throw new Error(
      'No tienes permiso para realizar esta acción. Tu rol es de solo lectura.',
    )
  }
}
