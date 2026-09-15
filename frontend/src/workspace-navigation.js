/* RiskIQ workspace navigation controller.
   React owns destination state; this controller owns category expansion only. */
(() => {
  const wired = new WeakSet()

  const wire = () => {
    const sidebar = document.querySelector('.ros-sidebar')
    if (!sidebar) return

    const groups = [...sidebar.querySelectorAll('.ros-command-menu .side-group')]
    groups.forEach((group, index) => {
      if (wired.has(group)) return
      const trigger = group.querySelector(':scope > .ros-category-trigger')
      if (!trigger) return
      wired.add(group)

      const closeSiblings = () => {
        groups.forEach(other => {
          if (other === group) return
          const otherTrigger = other.querySelector(':scope > .ros-category-trigger')
          other.classList.remove('is-open')
          otherTrigger?.setAttribute('aria-expanded', 'false')
        })
      }

      const setOpen = open => {
        if (open) closeSiblings()
        group.classList.toggle('is-open', open)
        trigger.setAttribute('aria-expanded', String(open))
      }

      // Keep the first category open on first render. The active destination
      // is promoted automatically when the user clicks an item below.
      setOpen(group.classList.contains('is-open') || index === 0)

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

      group.querySelectorAll(':scope > button:not(.ros-category-trigger)').forEach(item => {
        item.addEventListener('click', () => setOpen(true))
      })
    })
  }

  wire()
  new MutationObserver(wire).observe(document.documentElement, {childList:true, subtree:true})
})()
