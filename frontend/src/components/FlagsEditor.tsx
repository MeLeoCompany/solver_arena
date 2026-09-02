import { useState, type ReactNode } from 'react'

interface Props {
  parameterNames: string[]
  values: Record<string, string>
  onChange: (values: Record<string, string>) => void
  disabled?: boolean
}

const MAX_SUGGESTIONS = 8

function highlightMatch(name: string, query: string): ReactNode {
  const idx = name.toLowerCase().indexOf(query)
  if (idx === -1 || query === '') return name
  return (
    <>
      {name.slice(0, idx)}
      <mark>{name.slice(idx, idx + query.length)}</mark>
      {name.slice(idx + query.length)}
    </>
  )
}

export function FlagsEditor({ parameterNames, values, onChange, disabled }: Props) {
  const [query, setQuery] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [pasteText, setPasteText] = useState('')
  const [pasteError, setPasteError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const trimmedQuery = query.trim().toLowerCase()
  const suggestions = trimmedQuery
    ? parameterNames
        .filter((name) => name.toLowerCase().includes(trimmedQuery) && !(name in values))
        .slice(0, MAX_SUGGESTIONS)
    : []

  function addParameter(name: string) {
    onChange({ ...values, [name]: '' })
    setQuery('')
    setShowSuggestions(false)
  }

  function setValue(name: string, value: string) {
    onChange({ ...values, [name]: value })
  }

  function removeParameter(name: string) {
    const { [name]: _removed, ...rest } = values
    onChange(rest)
  }

  function handleCopyJson() {
    navigator.clipboard.writeText(JSON.stringify(values, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  function handleApplyJson() {
    let parsed: unknown
    try {
      parsed = JSON.parse(pasteText)
    } catch {
      setPasteError('Не похоже на валидный JSON')
      return
    }
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      setPasteError('Ожидается плоский JSON-объект вида {"параметр": "значение"}')
      return
    }
    const next: Record<string, string> = {}
    for (const [name, value] of Object.entries(parsed as Record<string, unknown>)) {
      next[name] = typeof value === 'string' ? value : JSON.stringify(value)
    }
    onChange(next)
    setPasteError(null)
    setPasteText('')
  }

  return (
    <div className="flags-editor">
      <div className="flags-editor__search">
        <input
          placeholder="Начните вводить имя параметра…"
          value={query}
          disabled={disabled}
          onChange={(e) => {
            setQuery(e.target.value)
            setShowSuggestions(true)
          }}
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
        />
        {showSuggestions && suggestions.length > 0 && (
          <ul className="flags-editor__suggestions">
            {suggestions.map((name) => (
              <li key={name} onMouseDown={() => addParameter(name)}>
                {highlightMatch(name, trimmedQuery)}
              </li>
            ))}
          </ul>
        )}
      </div>

      {Object.keys(values).length > 0 && (
        <div className="flags-editor__rows">
          {Object.entries(values).map(([name, value]) => (
            <div key={name} className="flags-editor__row">
              <span className="flags-editor__row-name">{name}</span>
              <input
                placeholder="значение"
                value={value}
                disabled={disabled}
                onChange={(e) => setValue(name, e.target.value)}
              />
              <button
                type="button"
                className="flags-editor__remove"
                disabled={disabled}
                onClick={() => removeParameter(name)}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      <details className="flags-editor__json-tools">
        <summary>Параметры как JSON — скопировать или вставить сохранённый набор</summary>
        <div className="flags-editor__json-tools-body">
          <div className="flags-editor__json-tools-row">
            <span className="flags-editor__json-tools-label">Текущие параметры →</span>
            <button
              type="button"
              className="button"
              disabled={disabled || Object.keys(values).length === 0}
              onClick={handleCopyJson}
            >
              {copied ? 'Скопировано ✓' : 'Скопировать'}
            </button>
          </div>

          <div className="flags-editor__json-tools-row flags-editor__json-tools-row--paste">
            <span className="flags-editor__json-tools-label">Сохранённый JSON →</span>
            <div className="flags-editor__json-tools-paste-input">
              <textarea
                placeholder={'{\n  "param1": "value1",\n  "param2": "value2"\n}'}
                value={pasteText}
                disabled={disabled}
                spellCheck={false}
                onChange={(e) => {
                  setPasteText(e.target.value)
                  setPasteError(null)
                }}
              />
              {pasteError && <div className="flags-editor__json-error">{pasteError}</div>}
              <button
                type="button"
                className="button"
                disabled={disabled || !pasteText.trim()}
                onClick={handleApplyJson}
              >
                Вставить (заменит текущие параметры)
              </button>
            </div>
          </div>
        </div>
      </details>
    </div>
  )
}
