/* RiskIQ navigation: two-level accordion inside the Control de mando menu. */
const SELECTOR = '.ros-command-menu .side-group'

function syncGroup(group, open) {
  group.classList.toggle('is-open', open)
  const label = group.querySelector('.side-group-label')
  if (label) {
    label.setAttribute('role', 'button')
    label.setAttribute('tabindex', '0')
    label.setAttribute('aria-expanded', String(open))
    label.setAttribute('aria-controls', `risk-group-${[...group.parentElement.children].indexOf(group)}`)
  }
}

function enhance(root = document) {
  root.querySelectorAll(SELECTOR).forEach((group, index) => {
    if (group.dataset.accordionReady) return
    group.dataset.accordionReady = '1'
    const label = group.querySelector('.side-group-label')
    const items = group.querySelectorAll('button')
    if (!label) return
    const id = `risk-group-${index}`
    items.forEach(button => button.setAttribute('data-risk-nav-item', '1'))
    items.forEach(button => button.parentElement?.setAttribute('id', id))
    syncGroup(group, false)
    const toggle = event => {
      event.preventDefault()
      event.stopPropagation()
      const open = !group.classList.contains('is-open')
      syncGroup(group, open)
    }
    label.addEventListener('click', toggle)
    label.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') toggle(event)
    })
  })
}

function boot() {
  enhance()
  const observer = new MutationObserver(() => enhance())
  observer.observe(document.body, {childList: true, subtree: true})
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, {once: true})
else boot()
