import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { wardrobe as wardrobeApi } from '../api/client'
import styles from './Wardrobe.module.css'

const CATEGORIES = ['all','top','bottom','outerwear','footwear','accessory','activewear','dress','formal','other']
const FORMALITIES = ['all','casual','casual_smart','smart','formal','activewear']

export default function Wardrobe() {
  const [items,    setItems]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [filters,  setFilters]  = useState({ category:'', formality:'', q:'' })
  const [total,    setTotal]    = useState(0)

  useEffect(() => { load() }, [filters])

  const load = async () => {
    setLoading(true)
    try {
      const params = {}
      if (filters.category)  params.category  = filters.category
      if (filters.formality) params.formality = filters.formality
      if (filters.q)         params.q         = filters.q
      const { data } = await wardrobeApi.list(params)
      setItems(data.results || [])
      setTotal(data.count  || 0)
    } finally {
      setLoading(false)
    }
  }

  const remove = async (id) => {
    if (!confirm('Remove this item?')) return
    await wardrobeApi.remove(id)
    load()
  }

  const set = k => v => setFilters(f => ({ ...f, [k]: v }))

  return (
    <div className="page-enter">
      <div className={styles.header}>
        <div>
          <p className="text-label">Your Wardrobe</p>
          <h2>{total} item{total !== 1 ? 's' : ''}</h2>
        </div>
        <Link to="/wardrobe/new" className="btn btn-primary">
          + Add item
        </Link>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        <input
          className="input"
          placeholder="Search by name, brand, material…"
          value={filters.q}
          onChange={e => set('q')(e.target.value)}
          style={{ flex: 1 }}
        />
        <select className="input" value={filters.category} onChange={e => set('category')(e.target.value)}>
          <option value="">All categories</option>
          {CATEGORIES.slice(1).map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase()+c.slice(1)}</option>)}
        </select>
        <select className="input" value={filters.formality} onChange={e => set('formality')(e.target.value)}>
          <option value="">All formalities</option>
          {FORMALITIES.slice(1).map(f => <option key={f} value={f}>{f.replace('_',' ')}</option>)}
        </select>
      </div>

      {loading ? (
        <div style={{display:'flex',justifyContent:'center',padding:'4rem'}}>
          <span className="spinner" />
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <span className="icon">◈</span>
          <h3>Your wardrobe is empty</h3>
          <p>Add your first item to get outfit recommendations.</p>
          <Link to="/wardrobe/new" className="btn btn-primary">Add first item</Link>
        </div>
      ) : (
        <div className={styles.grid}>
          {items.map(item => (
            <WardrobeCard key={item.id} item={item} onDelete={remove} />
          ))}
        </div>
      )}
    </div>
  )
}

function WardrobeCard({ item, onDelete }) {
  const formalityColor = {
    formal: 'badge-amber', smart: 'badge-amber',
    casual_smart: 'badge-sage', casual: 'badge-muted', activewear: 'badge-sage'
  }
  return (
    <div className={`${styles.card} card card-hover`}>
      {item.image ? (
        <img src={item.image} alt={item.name} className={styles.image} />
      ) : (
        <div className={styles.imagePlaceholder}>
          <span>{item.category?.[0]?.toUpperCase() || '?'}</span>
        </div>
      )}
      <div className={styles.cardBody}>
        <div className={styles.cardTop}>
          <span className={styles.name}>{item.name}</span>
          <span className="badge badge-muted">{item.category}</span>
        </div>
        <div className={styles.meta}>
          {item.brand && <span className="text-small text-muted">{item.brand}</span>}
          {item.colors?.length > 0 && (
            <div className={styles.colors}>
              {item.colors.map((c,i) => (
                <span key={i} className={styles.colorDot} style={{background: c}} title={c} />
              ))}
            </div>
          )}
        </div>
        <div className={styles.cardFooter}>
          <span className={`badge ${formalityColor[item.formality] || 'badge-muted'}`}>
            {item.formality?.replace('_',' ')}
          </span>
          <div style={{display:'flex',gap:'0.4rem'}}>
            <span className="text-small text-muted">{item.times_worn}× worn</span>
            <button className="btn btn-sm btn-danger" onClick={() => onDelete(item.id)}>✕</button>
          </div>
        </div>
      </div>
    </div>
  )
}
