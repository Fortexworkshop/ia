// Une erreur dans un élément ne doit pas effacer tout l'écran de supervision (OWASP A10).
import { Component } from 'react'

export default class ErrorBoundary extends Component {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error) {
    console.error(`[${this.props.name}]`, error)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className="notice error" role="alert">
        <span>
          « {this.props.name} » n'a pas pu s'afficher. Le reste de l'écran fonctionne.{' '}
          <button type="button" className="btn small" onClick={() => this.setState({ failed: false })}>
            Réessayer
          </button>
        </span>
      </div>
    )
  }
}
