import { useEffect, useState } from 'react'
import { createToken, listTokens, revokeToken } from '../api/tokens'
import type { ApiTokenCreatedResponse, ApiTokenResponse } from '../api/types'

export function TokensPage() {
  const [tokens, setTokens] = useState<ApiTokenResponse[] | null>(null)
  const [name, setName] = useState('')
  const [creating, setCreating] = useState(false)
  const [justCreated, setJustCreated] = useState<ApiTokenCreatedResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  function reload() {
    listTokens()
      .then(setTokens)
      .catch(() => setError('Не удалось загрузить токены'))
  }

  useEffect(reload, [])

  async function handleCreate() {
    if (!name.trim()) return
    setCreating(true)
    setError(null)
    try {
      const created = await createToken(name.trim())
      setJustCreated(created)
      setName('')
      reload()
    } catch {
      setError('Не удалось создать токен')
    } finally {
      setCreating(false)
    }
  }

  async function handleRevoke(id: number) {
    await revokeToken(id)
    if (justCreated?.id === id) setJustCreated(null)
    reload()
  }

  return (
    <div className="tokens-page">
      <h1>API-токены</h1>
      <p className="tokens-page__hint">
        Для доступа к API без браузера (например, из расчётного модуля) — заголовок{' '}
        <code>Authorization: Bearer &lt;token&gt;</code>. Срок жизни — 90 дней.
      </p>

      <div className="tokens-page__create">
        <input
          placeholder="Название (например, calc-module)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={creating}
        />
        <button
          type="button"
          className="button button--primary"
          disabled={creating || !name.trim()}
          onClick={handleCreate}
        >
          Создать токен
        </button>
      </div>

      {error && <div className="tokens-page__error">{error}</div>}

      {justCreated && (
        <div className="tokens-page__new-token">
          <div className="tokens-page__new-token-warning">
            Скопируйте сейчас — повторно показан не будет
          </div>
          <code className="tokens-page__new-token-value">{justCreated.token}</code>
          <button
            type="button"
            className="button"
            onClick={() => navigator.clipboard.writeText(justCreated.token)}
          >
            Копировать
          </button>
        </div>
      )}

      {tokens && (
        <table className="tokens-table">
          <thead>
            <tr>
              <th>Название</th>
              <th>Создан</th>
              <th>Истекает</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tokens.map((t) => (
              <tr key={t.id}>
                <td>{t.name}</td>
                <td>{new Date(t.created_at).toLocaleDateString()}</td>
                <td>{new Date(t.expires_at).toLocaleDateString()}</td>
                <td>
                  <button type="button" className="button button--danger" onClick={() => handleRevoke(t.id)}>
                    Отозвать
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
