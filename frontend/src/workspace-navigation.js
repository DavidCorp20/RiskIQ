/* RiskIQ workspace navigation controller.
   The sidebar is rendered by React, so navigation uses delegated events rather than
   attaching handlers to nodes that React may replace during a render. */
(() => {
  const getGroups = () => [...document.querySelectorAll('.ros-command-menu .side-group')]

  const setOpen = (group, open) => {
    const groups = getGroups()
    if (!group) return

    if (open) {
      groups.forEach(other => {
        if (other !== group) {
          other.classList.remove('is-open')
          other.querySelector('.ros-category-trigger')?.setAttribute('aria-expanded', 'false')
        }
      })
    }

    group.classList.toggle('is-open', open)
    group.querySelector('.ros-category-trigger')?.setAttribute('aria-expanded', String(open))
  }

  const ensureState = () => {
    const groups = getGroups()
    if (!groups.length) return

    // Preserve the currently open group. On the first render open Control.
    if (!groups.some(group => group.classList.contains('is-open'))) {
      setOpen(groups[0], true)
    }
  }

  document.addEventListener('click', event => {
    const trigger = event.target.closest?.('.ros-command-menu .ros-category-trigger')
    if (!trigger) return

    event.preventDefault()
    event.stopPropagation()

    const group = trigger.closest('.side-group')
    if (!group) return

    setOpen(group, !group.classList.contains('is-open'))
  }, true)

  document.addEventListener('keydown', event => {
    if (event.key !== 'Enter' && event.key !== ' ') return
    const trigger = event.target.closest?.('.ros-command-menu .ros-category-trigger')
    if (!trigger) return

    event.preventDefault()
    const group = trigger.closest('.side-group')
    if (group) setOpen(group, !group.classList.contains('is-open'))
  })

  // React can replace the sidebar after loading a dataset/page. Re-assert only
  // the open/closed state; do not attach duplicate listeners.
  new MutationObserver(ensureState).observe(document.documentElement, {
    childList: true,
    subtree: true
  })

  ensureState()
})()
