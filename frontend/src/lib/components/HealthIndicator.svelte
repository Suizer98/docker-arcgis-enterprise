<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { healthService, type HealthStatus } from '$lib/services/healthService';

  let healthStatus: HealthStatus = { status: 'checking' };
  let unsubscribe: (() => void) | null = null;

  onMount(() => {
    unsubscribe = healthService.subscribe((status) => {
      healthStatus = status;
    });
  });

  onDestroy(() => {
    if (unsubscribe) {
      unsubscribe();
    }
  });

  $: statusColor = healthStatus.status === 'healthy' ? 'bg-green-500' : 
                   healthStatus.status === 'unhealthy' ? 'bg-red-500' : 
                   'bg-yellow-500';
  
  $: statusText = healthStatus.status === 'healthy' ? 'API Healthy' : 
                  healthStatus.status === 'unhealthy' ? 'API Unhealthy' : 
                  'Checking...';
</script>

<div class="flex items-center space-x-2 text-sm">
  <!-- Flashing indicator -->
  <div class="flex items-center space-x-1">
    <div 
      class="w-2 h-2 rounded-full animate-pulse {statusColor}"
      title="{statusText}"
    ></div>
    <span class="text-muted-foreground">{statusText}</span>
  </div>
  
  <!-- Additional info for healthy status -->
  {#if healthStatus.status === 'healthy' && healthStatus.tools_count !== undefined}
    <span class="text-xs text-muted-foreground">
      • {healthStatus.tools_count} tools
    </span>
  {/if}
  
  <!-- Error info for unhealthy status -->
  {#if healthStatus.status === 'unhealthy' && healthStatus.error}
    <span class="text-xs text-red-500" title="{healthStatus.error}">
      • Error
    </span>
  {/if}
</div>
