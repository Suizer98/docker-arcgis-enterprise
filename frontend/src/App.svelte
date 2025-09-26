<script lang="ts">
  import { MapView } from './lib/Map'
  import { ChatSidebar } from './lib/Chat'
  import { ModeWatcher } from 'mode-watcher'
</script>

<ModeWatcher />
<main>
  <MapView />
  <ChatSidebar />
</main>

<style>
  :global(html, body) {
    margin: 0;
    padding: 0;
    height: 100vh;
    width: 100vw;
    overflow: hidden;
  }

  :global(#app) {
    height: 100vh;
    width: 100vw;
  }

  main {
    height: 100vh;
    width: 100vw;
    position: fixed;
    top: 0;
    left: 0;
  }
</style>
