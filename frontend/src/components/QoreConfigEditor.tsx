interface Props {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

export function QoreConfigEditor({ value, onChange, disabled }: Props) {
  return (
    <div className="qore-config-editor">
      <label htmlFor="qore-config" className="qore-config-editor__label">
        Конфигурация QORE (JSON, необязательно)
      </label>
      <textarea
        id="qore-config"
        className="qore-config-editor__textarea"
        value={value}
        disabled={disabled}
        spellCheck={false}
        placeholder={'{\n  "logs_config": {\n    "log_console_level": "info"\n  }\n}'}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}
