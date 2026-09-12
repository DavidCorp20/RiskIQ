/* Final workspace navigation controller. React owns destination state; this owns only category expansion. */
(() => {
  const ready = new WeakSet()
  const wire = () => {
    document.querySelectorAll('.ros-sidebar .ros-command-menu .side-group').forEach(group => {
      if (ready.has(group)) return
      const trigger = group.querySelector(':scope > .ros-category-trigger')
      if (!trigger) return
      ready.add(group)
      const setOpen = open => {
        group.classList.toggle('is-open', open)
        trigger.setAttribute('aria-expanded', String(open))
      }
      trigger.setAttribute('aria-expanded', 'false')
      trigger.addEventListener('click', event => {
        event.preventDefault()
        event.stopPropagation()
        setOpen(!group.classList.contains('is-open'))
      })
      trigger.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          setOpen(!group.classList.contains('is-open'))
        }
      })
    })
  }
  wire()
  new MutationObserver(wire).observe(document.documentElement, {childList:true, subtree:true})
})()
