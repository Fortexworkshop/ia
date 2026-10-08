// Grille personnalisable : ajouter, supprimer (avec annulation), régler, déplacer, réorganiser.
// Accessibilité : chaque déplacement a une alternative sans glisser (boutons, WCAG 2.5.7) et est
// annoncé aux lecteurs d'écran ; le catalogue est une <dialog> native (focus piégé par le navigateur).
import { useEffect, useRef, useState } from 'react'
import ErrorBoundary from '../components/ErrorBoundary.jsx'
import Icon from '../components/Icon.jsx'
import { SIZES, defaultLayout, loadLayout, make, ops, saveLayout } from './layout.js'
import { WIDGETS, titleOf } from './widgets.jsx'

const TYPES = Object.keys(WIDGETS)

export default function WidgetGrid() {
  const [layout, setLayout] = useState(() => loadLayout(TYPES))
  const [editing, setEditing] = useState(false)
  const [settingsFor, setSettingsFor] = useState(null)
  const [removed, setRemoved] = useState(null) // { widget, index } : pour « Annuler »
  const [announce, setAnnounce] = useState('')
  const [drag, setDrag] = useState(null) // affichage : { id, over, after }
  const dragRef = useRef(null) // logique : à jour immédiatement (l'état React ne l'est qu'au rendu suivant)
  const focusNext = useRef(null) // id d'élément à focaliser après le prochain rendu
  const dialog = useRef(null)
  const editButton = useRef(null)

  useEffect(() => saveLayout(layout), [layout])
  useEffect(() => {
    if (focusNext.current) {
      document.getElementById(focusNext.current)?.focus()
      focusNext.current = null
    }
  })

  const say = (text) => setAnnounce((prev) => (prev === text ? `${text} ` : text)) // force la relecture
  const position = (list, id) => `position ${list.findIndex((w) => w.id === id) + 1} sur ${list.length}`

  const move = (w, to, focusId) => {
    const next = ops.move(layout, w.id, to)
    if (next === layout) return
    setLayout(next)
    // en première / dernière position, la flèche correspondante est désactivée : focus sur l'autre
    const at = next.findIndex((x) => x.id === w.id)
    focusNext.current =
      at === 0 && focusId.endsWith('-back') ? `${w.id}-fwd` : at === next.length - 1 && focusId.endsWith('-fwd') ? `${w.id}-back` : focusId
    say(`${titleOf(w)} déplacé en ${position(next, w.id)}.`)
  }

  const remove = (w) => {
    const index = layout.findIndex((x) => x.id === w.id)
    setLayout(ops.remove(layout, w.id))
    setRemoved({ widget: w, index })
    if (settingsFor === w.id) setSettingsFor(null)
    focusNext.current = 'undo-remove'
    say(`${titleOf(w)} supprimé.`)
  }

  const undo = () => {
    if (!removed) return
    setLayout(ops.add(layout, removed.widget, removed.index))
    focusNext.current = `${removed.widget.id}-title`
    say(`${titleOf(removed.widget)} rétabli.`)
    setRemoved(null)
  }

  const add = (type) => {
    const def = WIDGETS[type]
    const w = make(type, def.defaultSize, { ...def.defaults })
    setLayout(ops.add(layout, w))
    dialog.current?.close()
    focusNext.current = `${w.id}-title`
    say(`${def.label} ajouté en dernière position.`)
    requestAnimationFrame(() => document.getElementById(w.id)?.scrollIntoView({ block: 'nearest' }))
  }

  const reset = () => {
    if (!window.confirm('Revenir à la disposition par défaut ? Vos éléments et consignes seront remplacés.')) return
    setLayout(defaultLayout())
    setRemoved(null)
    setSettingsFor(null)
    say('Disposition par défaut rétablie.')
  }

  const finish = () => {
    setEditing(false)
    setSettingsFor(null)
    setRemoved(null)
    focusNext.current = 'customize'
    say('Personnalisation terminée.')
  }

  // Glisser-déposer (souris) : insertion avant ou après l'élément survolé
  const onDragOver = (e, target) => {
    const d = dragRef.current
    if (!d || d.id === target.id) return
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    const r = e.currentTarget.getBoundingClientRect()
    // élément large : moitié haute / basse ; sinon moitié gauche / droite
    const after = r.width > r.height * 1.5 ? e.clientY > r.top + r.height / 2 : e.clientX > r.left + r.width / 2
    if (d.over !== target.id || d.after !== after) {
      dragRef.current = { ...d, over: target.id, after }
      setDrag(dragRef.current)
    }
  }
  const endDrag = () => {
    dragRef.current = null
    setDrag(null)
  }
  const onDrop = (e, target) => {
    e.preventDefault()
    const d = dragRef.current
    endDrag()
    if (!d || d.id === target.id) return
    const from = layout.findIndex((w) => w.id === d.id)
    const t = layout.findIndex((w) => w.id === target.id)
    const after = d.over === target.id ? d.after : false
    const to = after ? (from < t ? t : t + 1) : from < t ? t - 1 : t
    move(layout[from], to, `${d.id}-title`)
  }

  return (
    <section aria-labelledby="widgets-title" className="widgets-section">
      <div className="widgets-head">
        <h2 id="widgets-title" className={editing ? '' : 'sr-only'}>
          {editing ? 'Personnaliser la vue d’ensemble' : 'Tableau de bord'}
        </h2>
        {!editing ? (
          <button id="customize" ref={editButton} type="button" className="btn small quiet" onClick={() => setEditing(true)}>
            <Icon name="edit" /> Personnaliser
          </button>
        ) : (
          <div className="btn-row">
            <button type="button" className="btn small" onClick={() => dialog.current?.showModal()}>
              <Icon name="plus" /> Ajouter un élément
            </button>
            <button type="button" className="btn small quiet" onClick={reset}>
              Disposition par défaut
            </button>
            <button type="button" className="btn small primary" onClick={finish}>
              Terminer
            </button>
          </div>
        )}
      </div>

      {editing && (
        <p className="notice info small">
          <Icon name="info" />
          <span>
            Déplacez un élément en le faisant glisser par sa poignée, ou avec ses boutons flèches. La disposition est
            enregistrée sur ce poste. Le bandeau d'état du site reste toujours affiché.
          </span>
        </p>
      )}

      {removed && (
        <p className="notice">
          <span>« {titleOf(removed.widget)} » supprimé.</span>
          <button id="undo-remove" type="button" className="btn small" onClick={undo}>
            <Icon name="undo" /> Annuler
          </button>
        </p>
      )}

      {layout.length === 0 && (
        <p className="empty-state panel">
          <Icon name="info" /> La vue d'ensemble est vide. Utilisez « Personnaliser » puis « Ajouter un élément ».
        </p>
      )}

      <div className={`widgets ${editing ? 'editing' : ''}`}>
        {layout.map((w, i) => {
          const def = WIDGETS[w.type]
          const title = titleOf(w)
          const dropClass = drag?.over === w.id ? (drag.after ? 'drop-after' : 'drop-before') : ''
          return (
            <article
              key={w.id}
              id={w.id}
              className={`widget w-${w.size} t-${w.type} ${drag?.id === w.id ? 'dragging' : ''} ${dropClass}`}
              aria-labelledby={`${w.id}-title`}
              onDragOver={editing ? (e) => onDragOver(e, w) : undefined}
              onDrop={editing ? (e) => onDrop(e, w) : undefined}
            >
              <header className="widget-head">
                {editing && (
                  <span
                    className="grip"
                    aria-hidden="true"
                    draggable
                    title="Faire glisser pour déplacer"
                    onDragStart={(e) => {
                      e.dataTransfer.effectAllowed = 'move'
                      e.dataTransfer.setData('text/plain', w.id)
                      e.dataTransfer.setDragImage(e.currentTarget.closest('.widget'), 24, 24)
                      dragRef.current = { id: w.id }
                      // différé : modifier la page pendant dragstart annule le glisser dans Chrome
                      setTimeout(() => dragRef.current && setDrag(dragRef.current), 0)
                    }}
                    onDragEnd={endDrag}
                  >
                    <Icon name="grip" />
                  </span>
                )}
                <h2 id={`${w.id}-title`} tabIndex={-1}>
                  {title}
                </h2>
                {editing && (
                  <div className="widget-tools">
                    <button id={`${w.id}-back`} type="button" className="icon-btn" disabled={i === 0} onClick={() => move(w, i - 1, `${w.id}-back`)}>
                      <Icon name="back" />
                      <span className="sr-only">Déplacer avant : {title}</span>
                    </button>
                    <button id={`${w.id}-fwd`} type="button" className="icon-btn" disabled={i === layout.length - 1} onClick={() => move(w, i + 1, `${w.id}-fwd`)}>
                      <Icon name="forward" />
                      <span className="sr-only">Déplacer après : {title}</span>
                    </button>
                    <button
                      type="button"
                      className="icon-btn"
                      aria-expanded={settingsFor === w.id}
                      aria-controls={`${w.id}-settings`}
                      onClick={() => setSettingsFor(settingsFor === w.id ? null : w.id)}
                    >
                      <Icon name="gear" />
                      <span className="sr-only">Réglages : {title}</span>
                    </button>
                    <button type="button" className="icon-btn danger" onClick={() => remove(w)}>
                      <Icon name="trash" />
                      <span className="sr-only">Supprimer : {title}</span>
                    </button>
                  </div>
                )}
              </header>

              {editing && settingsFor === w.id && (
                <Settings widget={w} def={def} onChange={(patch) => setLayout((l) => ops.update(l, w.id, patch))} onClose={() => {
                  setSettingsFor(null)
                  focusNext.current = `${w.id}-title`
                }} />
              )}

              <div className="widget-body">
                <ErrorBoundary name={title}>
                  <def.Component config={w.config} />
                </ErrorBoundary>
              </div>
            </article>
          )
        })}
      </div>

      <dialog ref={dialog} className="catalog" aria-labelledby="catalog-title">
        <div className="catalog-head">
          <h2 id="catalog-title">Ajouter un élément</h2>
          <button type="button" className="btn small quiet" onClick={() => dialog.current?.close()}>
            Fermer
          </button>
        </div>
        <ul className="catalog-list">
          {TYPES.map((type) => (
            <li key={type}>
              <Icon name={WIDGETS[type].icon} />
              <div>
                <b>{WIDGETS[type].label}</b>
                <p className="muted small">{WIDGETS[type].description}</p>
              </div>
              <button type="button" className="btn small" onClick={() => add(type)}>
                Ajouter<span className="sr-only"> : {WIDGETS[type].label}</span>
              </button>
            </li>
          ))}
        </ul>
      </dialog>

      <p className="sr-only" role="status">
        {announce}
      </p>
    </section>
  )
}

function Settings({ widget, def, onChange, onClose }) {
  const id = `${widget.id}-settings`
  return (
    <form id={id} className="widget-settings" aria-label={`Réglages : ${titleOf(widget)}`} onSubmit={(e) => (e.preventDefault(), onClose())}>
      <div className="form-grid">
        <div className="field">
          <label htmlFor={`${id}-title`}>Titre</label>
          <input
            id={`${id}-title`}
            value={widget.title}
            placeholder={def.title(widget)}
            maxLength={60}
            onChange={(e) => onChange({ title: e.target.value })}
            aria-describedby={`${id}-title-help`}
          />
          <p id={`${id}-title-help`} className="help">
            Vide : titre par défaut.
          </p>
        </div>
        <fieldset className="field">
          <legend>Taille</legend>
          <div className="segmented">
            {def.sizes.map((s) => (
              <label key={s}>
                <input type="radio" name={`${id}-size`} value={s} checked={widget.size === s} onChange={() => onChange({ size: s })} />
                {SIZES[s].label}
              </label>
            ))}
          </div>
        </fieldset>
        {def.Settings && <def.Settings widget={widget} onChange={onChange} idPrefix={id} />}
      </div>
      <div className="btn-row">
        <button type="submit" className="btn small primary">
          Fermer les réglages
        </button>
      </div>
    </form>
  )
}
