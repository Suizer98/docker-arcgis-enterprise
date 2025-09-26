<script lang="ts">
  import { fly } from 'svelte/transition'
  import { Button } from '$lib/components/ui/button/index.js'
  import { aiService } from '$lib/services/aiService'

  export let messagesContainer: HTMLDivElement
  export let messages: Array<{id: string, role: 'user' | 'assistant', content: string, timestamp?: Date}>
  export let isLoading: boolean
  export let chatWidth: number

  // Copy message to clipboard
  async function copyMessage(content: string) {
    try {
      await navigator.clipboard.writeText(content)
      console.log('Message copied to clipboard')
    } catch (error) {
      console.error('Failed to copy message:', error)
    }
  }

  // Delete message
  function deleteMessage(messageId: string) {
    // This would need to be implemented in aiService
  }
</script>

<!-- Messages Container - Fixed height with scroll -->
<div 
  bind:this={messagesContainer}
  class="flex-1 overflow-y-auto p-4 space-y-3 min-h-0"
>
  {#each messages as message, messageIndex (messageIndex)}
    <div 
      class="p-3 rounded-lg group relative"
      class:max-w-xs={chatWidth < 400}
      class:max-w-sm={chatWidth >= 400}
      class:ml-auto={message.role === 'user'}
      class:bg-primary={message.role === 'user'}
      class:text-primary-foreground={message.role === 'user'}
      class:bg-muted={message.role === 'assistant'}
      transition:fly={{ x: message.role === 'user' ? 200 : -200, duration: 300, delay: messageIndex * 100 }}
    >
      <div class="whitespace-pre-wrap break-words">{message.content}</div>
      {#if message.timestamp}
        <div class="text-xs opacity-60 mt-1">
          {message.timestamp.toLocaleTimeString()}
        </div>
      {/if}
      
      <!-- Message Actions -->
      <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <div class="flex space-x-1">
          <Button
            variant="ghost"
            size="sm"
            onclick={() => copyMessage(message.content)}
            class="h-6 w-6 p-0"
            title="Copy message"
          >
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
          </Button>
          {#if message.role === 'assistant'}
            <Button
              variant="ghost"
              size="sm"
              onclick={() => deleteMessage(message.id)}
              class="h-6 w-6 p-0"
              title="Delete message"
            >
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
              </svg>
            </Button>
          {/if}
        </div>
      </div>
    </div>
  {/each}
  
  <!-- Typing Indicator -->
  {#if isLoading}
    <div 
      class="p-3 rounded-lg bg-muted max-w-xs"
      transition:fly={{ x: -200, duration: 300 }}
    >
      <div class="flex items-center space-x-2">
        <div class="flex space-x-1">
          <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
          <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
          <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
        </div>
        <span class="text-sm text-gray-500">AI is thinking...</span>
      </div>
    </div>
  {/if}
</div>
