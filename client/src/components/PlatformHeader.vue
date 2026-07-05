<template>
  <!--
    平台 Header 适配组件
    - PC：渲染 PC Header（页面级 Header）
    - TV/Mobile：不渲染（Header 由各自 Layout 提供）
  -->
  <component
    v-if="isPC"
    :is="pcHeader"
    v-bind="$attrs"
    :show-type-filters="showTypeFilters"
    :show-layout-toggle="showLayoutToggle"
    :layout="layout"
    @layout-change="$emit('layout-change', $event)"
    @home-click="$emit('home-click')"
  />
</template>

<script setup lang="ts">
import { usePlatform } from '@/composables/usePlatform'
import PcHeader from '@/components/pc/Header.vue'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  showTypeFilters?: boolean
  showLayoutToggle?: boolean
  layout?: 'vertical' | 'horizontal'
}>()

defineEmits<{
  (e: 'layout-change', layout: 'vertical' | 'horizontal'): void
  (e: 'home-click'): void
}>()

const { isPC } = usePlatform()
</script>
