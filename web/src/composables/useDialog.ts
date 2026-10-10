import { onBeforeUnmount, watch, type Ref } from 'vue'

/** Native modal dialogs own focus trapping, inert background and focus restoration. */
export function useDialog(dialog: Ref<HTMLDialogElement | null>, visible: () => boolean) {
  watch(
    [dialog, visible],
    ([element, open]) => {
      if (!element) return
      if (open && !element.open) element.showModal()
      else if (!open && element.open) element.close()
    },
    { flush: 'post' },
  )
  onBeforeUnmount(() => {
    dialog.value?.close()
  })
}
