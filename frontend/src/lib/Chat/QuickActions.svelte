<script lang="ts">
  import { Button } from '$lib/components/ui/button/index.js'

  export let isLoading: boolean
  export let onQuickAction: (action: string) => void

  let isExpanded = true

  function toggleExpanded() {
    isExpanded = !isExpanded
  }

  function handleQuickActionClick(action: string) {
    onQuickAction(action)
    // Auto-collapse after action is triggered
    isExpanded = false
  }
</script>

<div class="mb-3 min-h-[2rem]">
  <div class="flex items-center justify-between mb-1">
    <div class="text-sm font-medium text-gray-600">Quick Actions:</div>
    <Button 
      variant="ghost" 
      size="sm" 
      onclick={toggleExpanded}
      class="p-1 h-5 w-5 hover:bg-accent hover:text-accent-foreground"
      title={isExpanded ? 'Hide quick actions' : 'Show quick actions'}
    >
      {#if isExpanded}
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
        </svg>
      {:else}
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
        </svg>
      {/if}
    </Button>
  </div>
  
  <div class="transition-all duration-200 ease-in-out overflow-hidden" style="max-height: {isExpanded ? '3.5rem' : '0'};">
    <div class="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
      <Button 
        variant="outline" 
        size="sm" 
        onclick={() => handleQuickActionClick('Get my current location using geolocation')}
        disabled={isLoading}
        class="text-xs flex-1 sm:flex-none"
      >
        📍 Current Location
      </Button>
      <Button 
        variant="outline" 
        size="sm" 
        onclick={() => handleQuickActionClick('What is the current zoom level?')}
        disabled={isLoading}
        class="text-xs flex-1 sm:flex-none"
      >
        🔍 Current Zoom
      </Button>
      <Button 
        variant="outline" 
        size="sm" 
        onclick={() => handleQuickActionClick('Draw a line from my current location to a nearby point')}
        disabled={isLoading}
        class="text-xs flex-1 sm:flex-none"
      >
        📏 Draw Line
      </Button>
    </div>
  </div>
</div>
