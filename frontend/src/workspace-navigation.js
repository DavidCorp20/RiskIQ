/* Final workspace navigation controller. React owns destination state; this owns only category expansion. */
(() => {
  const ready = new WeakSet()
  const wire = () => {
    const groups = [...document.querySelectorAll('.ros-sidebar .ros-command-menu .side-group')]
    groups.forEach((group, index) => {
      if (ready.has(group)) return
      const trigger = group.querySelector(':scope > .ros-category-trigger')
      if (!trigger) return
      ready.add(group)

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

      const initiallyOpen = group.classList.contains('is-open') || index === 0
      setOpen(initiallyOpen)

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
