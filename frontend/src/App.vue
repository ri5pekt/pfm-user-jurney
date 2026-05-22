<template>
  <RouterView v-slot="{ Component }">
    <keep-alive :include="['DashboardView']">
      <component :is="Component" />
    </keep-alive>
  </RouterView>
</template>
