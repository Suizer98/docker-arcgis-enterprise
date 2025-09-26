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
  
  // Draggable and resizable state
  let chatWidth = 420 // Default width
  let isDragging = false
  let isResizing = false
  let dragStartX = 0
  let resizeStartX = 0
  let resizeStartWidth = 0
  
  // Get maximum width (half screen on both desktop and mobile)
  function getMaxWidth() {
    if (typeof window !== 'undefined') {
      return Math.floor(window.innerWidth / 2) // Half width on both desktop and mobile
    }
    return 400 // Default fallback
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
    // Set half-width on mobile
    if ($isMobile) {
      chatWidth = Math.floor(window.innerWidth / 2)
    }
    initialized = true
  }

  // Auto-scroll when messages change (debounced)
  let scrollTimeout: ReturnType<typeof setTimeout>
  $: if (messages.length > 0) {
    clearTimeout(scrollTimeout)
    scrollTimeout = setTimeout(scrollToBottom, 100)
  }

  function toggleSidebar() {
    isOpen = !isOpen
    
    // Auto-scroll when opening sidebar
    if (isOpen) {
      setTimeout(scrollToBottom, 200)
    }
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

  // Drag functions
  function handleDragStart(event: MouseEvent) {
    isDragging = true
    dragStartX = event.clientX
    document.addEventListener('mousemove', handleDragMove)
    document.addEventListener('mouseup', handleDragEnd)
    event.preventDefault()
  }

  function handleDragMove(event: MouseEvent) {
    if (!isDragging) return
    const deltaX = event.clientX - dragStartX
    const maxWidth = getMaxWidth()
    
    // On mobile, don't allow dragging - keep half width
    if ($isMobile) return
    
    const newWidth = Math.max(280, Math.min(maxWidth, chatWidth - deltaX))
    chatWidth = newWidth
    dragStartX = event.clientX
  }

  function handleDragEnd() {
    isDragging = false
    document.removeEventListener('mousemove', handleDragMove)
    document.removeEventListener('mouseup', handleDragEnd)
  }

  // Resize functions
  function handleResizeStart(event: MouseEvent) {
    isResizing = true
    resizeStartX = event.clientX
    resizeStartWidth = chatWidth
    document.addEventListener('mousemove', handleResizeMove)
    document.addEventListener('mouseup', handleResizeEnd)
    event.preventDefault()
    event.stopPropagation()
  }

  function handleResizeMove(event: MouseEvent) {
    if (!isResizing) return
    const deltaX = event.clientX - resizeStartX
    const maxWidth = getMaxWidth()
    
    // On mobile, don't allow resizing - keep half width
    if ($isMobile) return
    
    const newWidth = Math.max(280, Math.min(maxWidth, resizeStartWidth - deltaX))
    chatWidth = newWidth
  }

  function handleResizeEnd() {
    isResizing = false
    document.removeEventListener('mousemove', handleResizeMove)
    document.removeEventListener('mouseup', handleResizeEnd)
  }
</script>

<!-- Chat Toggle Button (only show when sidebar is closed) -->
{#if !isOpen}
  <Button 
    class="fixed top-4 right-4 z-[9999] size-10 bg-background/95 backdrop-blur-sm border-border hover:bg-accent hover:text-accent-foreground shadow-lg dark:bg-black dark:text-white dark:border-gray-700 dark:hover:bg-gray-800"
    onclick={toggleSidebar}
    variant="outline"
    size="icon"
  >
    <svg 
      class="w-5 h-5" 
      fill="none" 
      stroke="currentColor" 
      viewBox="0 0 24 24"
    >
      <path 
        stroke-linecap="round" 
        stroke-linejoin="round" 
        stroke-width="2" 
        d="M4 6h16M4 12h16M4 18h16"
      />
    </svg>
  </Button>
{/if}

<!-- Chat Sidebar -->
<div 
  class="fixed top-0 right-0 h-full z-40 transform transition-transform duration-300 ease-in-out flex"
  class:translate-x-full={!isOpen}
  class:translate-x-0={isOpen}
  class:w-full={!$isMobile && chatWidth < 400}
  class:w-80={!$isMobile && chatWidth >= 400 && chatWidth < 600}
  style="width: {$isMobile ? '70%' : (chatWidth >= 600 ? chatWidth + 'px' : 'auto')};"
>
  <Card class="h-full rounded-none border-r-0 border-t-0 border-b-0 flex flex-col w-full relative">
    <!-- Draggable Header -->
    <CardHeader 
      class="pb-3 flex-shrink-0 select-none {$isMobile ? '' : 'cursor-move'}"
      onmousedown={$isMobile ? undefined : handleDragStart}
    >
      <div class="flex items-center justify-between">
        <CardTitle class="text-lg">Docker ArcGIS Enterprise + AI</CardTitle>
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
          <!-- Close Button -->
          <Button 
            variant="ghost" 
            size="sm" 
            onclick={toggleSidebar}
            class="p-1 h-8 w-8 hover:bg-accent hover:text-accent-foreground text-foreground"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </Button>
        </div>
      </div>
    </CardHeader>
    
    <!-- Messages Container -->
    <ChatMessages 
      bind:messagesContainer
      {messages}
      {isLoading}
      {chatWidth}
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
    
    <!-- Resize Handle -->
    {#if !$isMobile}
      <div 
        class="absolute left-0 top-0 bottom-0 w-1 cursor-ew-resize hover:bg-blue-500 hover:opacity-50 transition-opacity"
        onmousedown={handleResizeStart}
        role="button"
        tabindex="0"
        aria-label="Resize chat sidebar"
      ></div>
    {/if}
  </Card>
</div>