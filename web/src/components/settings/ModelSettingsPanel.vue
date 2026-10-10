<script setup lang="ts">
import { reactive, toRefs } from 'vue'
import { useModelSettings } from '@/composables/useModelSettings'
import { providerChoices, choiceGroups } from '@/config/model-provider-choices'
import { getModelProvider } from '@/config/model-providers'
import IconSymbol from '@/components/common/IconSymbol.vue'
import ModelCatalogPicker from './ModelCatalogPicker.vue'
import ModelProfileEditor from './ModelProfileEditor.vue'
const editor = reactive(useModelSettings())
const {
  settings,
  mode,
  catalogOpen,
  modelOptions,
  draft,
  discovering,
  canDiscover,
  discoveryMessage,
  findPreset,
  profileProviderName,
  profileCredential,
  selectProfile,
  makeDefault,
  showProviderPicker,
  closeEditor,
  beginAdd,
  discoverModels,
  useCatalogModel,
} = toRefs(editor)
</script>
<template>
  <section class="model-settings glass-card">
    <header class="panel-heading">
      <div>
        <p>Model providers</p>
        <h2>模型</h2>
        <span>添加模型服务，并选择聊天时默认使用的模型。</span>
      </div>
      <button
        v-if="mode === 'list'"
        type="button"
        class="primary-button add-button"
        data-testid="add-model"
        @click="showProviderPicker"
      >
        <IconSymbol name="plus" :size="15" />添加模型
      </button>
    </header>

    <div v-if="mode === 'list'" class="profile-list">
      <article v-for="item in settings.modelProfiles" :key="item.id" class="profile-row">
        <button type="button" class="profile-main" :aria-label="`编辑 ${item.name}`" @click="selectProfile(item.id)">
          <span class="provider-mark" :class="item.provider">{{
            findPreset(item.baseUrl)?.name.slice(0, 2) || getModelProvider(item.provider).monogram
          }}</span>
          <span class="profile-copy">
            <span
              ><strong>{{ item.name }}</strong
              ><i v-if="item.isDefault">默认</i></span
            >
            <small>{{ profileProviderName(item) }} · {{ item.model }}</small>
          </span>
          <span class="credential-state" :class="profileCredential(item).tone"
            ><i />{{ profileCredential(item).label }}</span
          >
        </button>
        <button v-if="!item.isDefault" type="button" class="default-action" :disabled="settings.saving" @click="makeDefault(item.id)">
          设为默认
        </button>
        <button type="button" class="edit-action" :aria-label="`编辑 ${item.name}`" @click="selectProfile(item.id)">
          ›
        </button>
      </article>

      <div v-if="!settings.modelProfiles.length" class="empty-profile">
        <span class="empty-icon"><IconSymbol name="brain" :size="25" /></span>
        <h3>连接你的第一个模型</h3>
        <p>选择云端服务或当前设备上的模型服务。</p>
        <button type="button" class="primary-button" @click="showProviderPicker">选择模型服务</button>
      </div>
    </div>

    <section v-else-if="mode === 'providers'" class="provider-picker" data-testid="provider-picker">
      <button type="button" class="back-button" @click="closeEditor">‹ 返回模型列表</button>
      <div class="picker-heading">
        <h3>添加模型服务</h3>
        <p>先选择服务，再填写密钥和模型。每次只处理一个配置。</p>
      </div>
      <div v-for="group in choiceGroups" :key="group" class="choice-group">
        <h4>{{ group }}</h4>
        <div class="choice-grid">
          <button
            v-for="choice in providerChoices.filter((item) => item.group === group)"
            :key="choice.id"
            type="button"
            class="provider-choice"
            :data-provider-choice="choice.id"
            @click="beginAdd(choice)"
          >
            <span class="provider-mark compatible">{{ choice.monogram }}</span>
            <span
              ><strong>{{ choice.name }}</strong
              ><small>{{ choice.description }}</small></span
            >
            <i>›</i>
          </button>
        </div>
      </div>
    </section>

    <ModelProfileEditor v-else :editor="editor" />

    <ModelCatalogPicker
      v-if="catalogOpen"
      :models="modelOptions"
      :selected-model="draft.model"
      :loading="discovering"
      :can-refresh="canDiscover"
      :message="discoveryMessage"
      @close="catalogOpen = false"
      @refresh="discoverModels"
      @select="useCatalogModel"
    />
  </section>
</template>
<style scoped lang="scss">
@use '@/styles/model-settings';
</style>
