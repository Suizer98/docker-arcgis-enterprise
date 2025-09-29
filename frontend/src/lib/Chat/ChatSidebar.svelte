<script lang="ts">
  import { fly } from 'svelte/transition'
  import { Button } from '$lib/components/ui/button/index.js'
  import { Input } from '$lib/components/ui/input'
  import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card'
  import { aiService } from '$lib/services/aiService'
  import { isMobile } from '$lib/stores/mobileStore'
  import { toggleMode } from 'mode-watcher'
  import ChatMessages from './ChatMessages.svelte'
  import ChatInput from './ChatInput.svelte'
  import HealthIndicator from '$lib/components/HealthIndicator.svelte'

  export let isOpen = true

  let input = ''
  let messages: Array<{id: string, role: 'user' | 'assistant', content: string, timestamp?: Date}> = []
  let isLoading = false
  
  // Initialize with simple greeting
  function initializeChat() {
    if (messages.length === 0) {
      aiService.addMessage('assistant', 'Hi! I\'m your Docker ArcGIS Enterprise + AI Assistant. How can I help you with maps and geospatial data today?')
      updateMessages()
    }
  }
  
  // Auto-scroll reference
  let messagesContainer: HTMLDivElement

  // Update messages when they change
  function updateMessages() {
    messages = aiService.getMessages()
  }

  // Auto-scroll to bottom
  function scrollToBottom() {
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight
    }
  }

  // Initialize chat on component mount (only once)
  let initialized = false
  $: if (typeof window !== 'undefined' && !initialized) {
    initializeChat()
    initialized = true
  }

  // Auto-scroll when messages change (debounced)
  let scrollTimeout: ReturnType<typeof setTimeout>
  $: if (messages.length > 0) {
    clearTimeout(scrollTimeout)
    scrollTimeout = setTimeout(scrollToBottom, 100)
  }

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault()
    const userInput = input.trim()
    
    if (!userInput || isLoading) return

    // Clear input immediately
    input = ''
    
    // Set loading state
    isLoading = true
    updateMessages()

    try {
      // Process user input through AI service
      const result = await aiService.processUserInput(userInput)
      
      // Update messages after processing
      updateMessages()
    } catch (error) {
      console.error('Error processing user input:', error)
      
      // Add user-friendly error message
      let errorMessage = 'Sorry, I encountered an issue processing your request. Please try again.'
      
      aiService.addMessage('assistant', errorMessage)
      updateMessages()
    } finally {
      // Clear loading state
      isLoading = false
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSubmit(new Event('submit') as SubmitEvent)
    }
  }
</script>

<!-- Full Screen Chat -->
<div class="h-full w-full flex">
  <Card class="h-full w-full rounded-none flex flex-col relative">
    <!-- Header -->
    <CardHeader class="pb-3 flex-shrink-0">
      <div class="flex items-center justify-between">
        <div class="flex flex-col space-y-1">
          <CardTitle class="text-lg">Docker ArcGIS Enterprise + AI</CardTitle>
          <HealthIndicator />
        </div>
        <div class="flex space-x-2">
          <!-- Theme Toggle Button -->
          <Button 
            variant="ghost" 
            size="sm" 
            onclick={toggleMode}
            class="p-1 h-8 w-8 relative"
            title="Toggle theme"
          >
            <svg class="w-4 h-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="5"/>
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
            </svg>
            <svg class="absolute w-4 h-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
            <span class="sr-only">Toggle theme</span>
          </Button>
        </div>
      </div>
    </CardHeader>
    
    <!-- Messages Container -->
    <ChatMessages 
      bind:messagesContainer
      {messages}
      {isLoading}
    />
    
    <!-- Input -->
    <div class="flex-shrink-0 p-4 border-t bg-background">
      <ChatInput 
        bind:input
        {isLoading}
        onsubmit={handleSubmit}
        onkeydown={handleKeydown}
      />
    </div>
  </Card>
</div>