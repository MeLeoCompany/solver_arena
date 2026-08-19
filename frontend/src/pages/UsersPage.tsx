import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { ApiError } from '../api/client'
import { createUser, deleteUser, listUsers } from '../api/users'
import type { UserAdminResponse, UserCreatedResponse } from '../api/types'

export function UsersPage() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<UserAdminResponse[] | null>(null)
  const [username, setUsername] = useState('')
  const [creating, setCreating] = useState(false)
  const [justCreated, setJustCreated] = useState<UserCreatedResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  function reload() {
    listUsers()
      .then(setUsers)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Не удалось загрузить пользователей'))
  }

  useEffect(reload, [])

  async function handleCreate() {
    if (!username.trim()) return
    setCreating(true)
    setError(null)
    try {
      const created = await createUser(username.trim())
      setJustCreated(created)
      setUsername('')
      reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не удалось создать пользователя')
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteUser(id)
      if (justCreated?.id === id) setJustCreated(null)
      reload()
    } catch {
      setError('Не удалось удалить пользователя')
    }
  }

  return (
    <div className="tokens-page">
      <h1>Пользователи</h1>
      <p className="tokens-page__hint">
        Права пока бинарные — обычный пользователь или админ. Новые пользователи всегда создаются
        без прав администратора.
      </p>

      <div className="tokens-page__create">
        <input
          placeholder="Имя пользователя"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={creating}
        />
        <button
          type="button"
          className="button button--primary"
          disabled={creating || !username.trim()}
          onClick={handleCreate}
        >
          Создать пользователя
        </button>
      </div>

      {error && <div className="tokens-page__error">{error}</div>}

      {justCreated && (
        <div className="tokens-page__new-token">
          <div className="tokens-page__new-token-warning">
            Пароль для «{justCreated.username}» — скопируйте сейчас, повторно показан не будет
          </div>
          <code className="tokens-page__new-token-value">{justCreated.password}</code>
          <button
            type="button"
            className="button"
            onClick={() => navigator.clipboard.writeText(justCreated.password)}
          >
            Копировать
          </button>
        </div>
      )}

      {users && (
        <table className="tokens-table">
          <thead>
            <tr>
              <th>Имя пользователя</th>
              <th>Права</th>
              <th>Создан</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>{u.is_admin ? 'админ' : 'пользователь'}</td>
                <td>{new Date(u.created_at).toLocaleDateString()}</td>
                <td>
                  {u.username !== currentUser?.username && (
                    <button type="button" className="button button--danger" onClick={() => handleDelete(u.id)}>
                      Удалить
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
