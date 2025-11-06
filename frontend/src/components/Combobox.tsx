import { useEffect, useMemo, useRef, useState, KeyboardEvent } from 'react';

type Option = { label: string; value: string; group?: string };

type ComboboxProps = {
  options: Option[];
  label?: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
};

const Combobox = ({ options, placeholder, value, onChange }: ComboboxProps) => {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState<string>('');
  const containerRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    const term = inputValue.trim().toLowerCase();
    if (!term) return options;
    return options.filter((option) => option.label.toLowerCase().includes(term));
  }, [inputValue, options]);

  useEffect(() => {
    if (!open) {
      const selected = options.find((option) => option.value === value);
      setInputValue(selected ? selected.label : '');
    }
  }, [open, options, value]);

  useEffect(() => {
    setInputValue(options.find((option) => option.value === value)?.label || '');
  }, [value, options]);

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const grouped = useMemo(() => {
    const groups = new Map<string | undefined, Option[]>();
    filtered.forEach((option) => {
      const key = option.group || '';
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(option);
    });
    return Array.from(groups.entries());
  }, [filtered]);

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <input
        value={inputValue}
        placeholder={placeholder}
        onChange={(event) => {
          setInputValue(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(event: KeyboardEvent<HTMLInputElement>) => {
          if (event.key === 'Escape') {
            setOpen(false);
          }
        }}
        style={{ width: '100%', padding: '0.6rem', marginTop: '0.4rem' }}
      />
      {open && (
        <div
          style={{
            position: 'absolute',
            zIndex: 10,
            top: 'calc(100% + 0.25rem)',
            left: 0,
            right: 0,
            maxHeight: '16rem',
            overflowY: 'auto',
            background: '#fff',
            borderRadius: '0.5rem',
            boxShadow: '0 12px 30px -12px rgba(15, 23, 42, 0.35)',
            border: '1px solid #e2e8f0'
          }}
        >
          {grouped.length === 0 && (
            <div style={{ padding: '0.75rem', color: '#64748b' }}>No matches</div>
          )}
          {grouped.map(([group, items]) => (
            <div key={group || 'default'}>
              {group && (
                <div
                  style={{
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    padding: '0.5rem 0.75rem',
                    textTransform: 'uppercase',
                    color: '#94a3b8'
                  }}
                >
                  {group}
                </div>
              )}
              {items.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  onClick={() => {
                    onChange(item.value);
                    setOpen(false);
                  }}
                  style={{
                    display: 'block',
                    width: '100%',
                    textAlign: 'left',
                    padding: '0.6rem 0.75rem',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer'
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Combobox;
