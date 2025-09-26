import { writable } from 'svelte/store';

// Global mobile state
export const isMobile = writable(false);

// Mobile breakpoint
const MOBILE_BREAKPOINT = 768;

// Initialize mobile state
if (typeof window !== 'undefined') {
  isMobile.set(window.innerWidth < MOBILE_BREAKPOINT);

  // Listen for window resize
  window.addEventListener('resize', () => {
    isMobile.set(window.innerWidth < MOBILE_BREAKPOINT);
  });
}

// Helper function to check if mobile
export function checkIsMobile(): boolean {
  if (typeof window !== 'undefined') {
    return window.innerWidth < MOBILE_BREAKPOINT;
  }
  return false;
}
