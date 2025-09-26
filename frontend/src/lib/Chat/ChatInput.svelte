<script lang="ts">
  import { Input } from '$lib/components/ui/input'
  import { Button } from '$lib/components/ui/button/index.js'

  export let input: string
  export let isLoading: boolean
  export let onsubmit: (event: SubmitEvent) => void
  export let onkeydown: (event: KeyboardEvent) => void
</script>

<!-- Input Form -->
<form onsubmit={onsubmit} class="flex space-x-2">
  <Input 
    bind:value={input}
    placeholder="Ask me to navigate..."
    onkeydown={onkeydown}
    class="flex-1"
    disabled={isLoading}
  />
  <Button type="submit" size="sm" disabled={isLoading}>
    {isLoading ? 'Sending...' : 'Send'}
  </Button>
</form>
