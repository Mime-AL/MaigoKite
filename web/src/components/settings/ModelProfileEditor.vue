<script setup lang="ts">
import { toRefs, type UnwrapNestedRefs } from 'vue'
import type { useModelSettings } from '@/composables/useModelSettings'
import { MODEL_PROVIDERS, COMPATIBLE_PROVIDER_PRESETS } from '@/config/model-providers'
import IconSymbol from '@/components/common/IconSymbol.vue'
const props = defineProps<{ editor: UnwrapNestedRefs<ReturnType<typeof useModelSettings>> }>()
const {
  settings,
  draft,
  compatiblePreset,
  provider,
  displayProviderName,
  apiKey,
  revealKey,
  endpointChanged,
  keyRequired,
  modelOptions,
  canDiscover,
  discovering,
  selectedModelInfo,
  discoveryMessage,
  discoveredModels,
  isDirty,
  canSave,
  closeEditor,
  save,
  openCatalog,
  discoverModels,
  handleProviderChange,
  handlePresetChange,
  remove,
  makeDefault,
} = toRefs(props.editor)
</script>

<template>
  <form class="profile-editor" @submit.prevent="save">
    <header class="editor-heading">
      <button type="button" class="back-button" @click="closeEditor">‹ 返回模型列表</button>
      <div class="editor-title">
        <span class="provider-mark" :class="draft.provider">{{
          compatiblePreset?.name.slice(0, 2) || provider.monogram
        }}</span>
        <span
          ><small>{{ draft.id ? '编辑模型配置' : '添加模型配置' }}</small>
          <h3>{{ displayProviderName }}</h3></span
        >
        <i v-if="draft.isDefault" class="default-pill">默认</i>
      </div>
    </header>

    <div class="editor-body">
      <label class="form-field">
        <span>配置名称 <b>必填</b></span>
        <input
          v-model.trim="draft.name"
          data-testid="profile-name"
          maxlength="80"
          placeholder="例如：工作区 DeepSeek"
        />
        <small>用于在聊天框和默认模型列表中辨认这个配置。</small>
      </label>

      <label v-if="provider.apiKeyMode !== 'none'" class="form-field">
        <span
          >API Key <b>{{ keyRequired ? '必填' : '按需' }}</b></span
        >
        <span class="secret">
          <input
            v-model="apiKey"
            data-testid="api-key"
            :type="revealKey ? 'text' : 'password'"
            autocomplete="new-password"
            :placeholder="draft.credentialConfigured ? '已配置；留空继续使用' : '粘贴 API Key'"
          />
          <button
            type="button"
            :aria-label="revealKey ? '隐藏 API Key' : '显示 API Key'"
            @click="revealKey = !revealKey"
          >
            <IconSymbol :name="revealKey ? 'eye-off' : 'eye'" :size="16" />
          </button>
        </span>
        <small v-if="endpointChanged" class="warning"
          >端点或接口类型已变化，请输入对应的新 Key；旧 Key 不会发送到新端点。</small
        >
        <small v-else-if="draft.credentialConfigured" class="credential-confirmed"
          ><i />密钥已配置；留空表示继续使用。</small
        >
        <small v-else>填写此模型服务使用的密钥。</small>
      </label>

      <div class="form-field model-field">
        <span>模型 <b>必填</b></span>
        <div class="model-input-row">
          <input v-model.trim="draft.model" data-testid="model-id" :placeholder="provider.modelPlaceholder" />
          <button
            v-if="modelOptions.length"
            type="button"
            class="secondary-button"
            data-testid="browse-models"
            @click="openCatalog"
          >
            选择模型
          </button>
          <button
            type="button"
            class="secondary-button discover-button"
            :disabled="!canDiscover || discovering"
            :aria-busy="discovering || undefined"
            data-testid="discover-models"
            @click="discoverModels"
          >
            <IconSymbol v-if="!discovering" name="refresh" :size="14" />{{ discovering ? '正在获取…' : '从服务获取' }}
          </button>
        </div>
        <small v-if="selectedModelInfo" class="model-meta">{{ selectedModelInfo }}</small>
        <small v-else-if="discoveryMessage" :class="{ warning: !discoveredModels.length }">{{
          discoveryMessage
        }}</small>
        <small v-else>可自动读取服务端模型目录；目录不可用时也可以手工输入准确的模型 ID。</small>
      </div>

      <details class="custom-settings">
        <summary>
          <span><strong>自定义设置</strong><small>接口类型、服务预设与 Base URL</small></span>
          <i>›</i>
        </summary>
        <div class="custom-settings-body">
          <label class="form-field">
            <span>接口类型</span>
            <select data-testid="provider-type" :value="draft.provider" @change="handleProviderChange">
              <option v-for="item in MODEL_PROVIDERS" :key="item.id" :value="item.id">
                {{ item.name }}
              </option>
            </select>
          </label>
          <label v-if="draft.provider === 'openai_compatible'" class="form-field">
            <span>服务预设</span>
            <select data-testid="preset-select" :value="compatiblePreset?.id || ''" @change="handlePresetChange">
              <option value="">自定义地址</option>
              <option v-for="item in COMPATIBLE_PROVIDER_PRESETS" :key="item.id" :value="item.id">
                {{ item.name }}
              </option>
            </select>
          </label>
          <label class="form-field full">
            <span>{{ provider.baseUrlLabel }}</span>
            <input
              v-model.trim="draft.baseUrl"
              data-testid="base-url"
              type="url"
              :placeholder="provider.baseUrlPlaceholder"
            />
            <small>{{ provider.baseUrlHelp }}</small>
          </label>
        </div>
      </details>

      <p v-if="settings.validation" class="validation" :class="{ ok: settings.validation.ok }">
        <IconSymbol :name="settings.validation.ok ? 'check' : 'alert'" :size="15" />{{ settings.validation.message }}
      </p>
    </div>

    <footer class="editor-footer">
      <div>
        <button v-if="draft.id" type="button" class="danger-button" :disabled="settings.saving" @click="remove">删除配置</button>
        <button v-if="draft.id && !draft.isDefault" type="button" class="secondary-button" :disabled="settings.saving" @click="makeDefault()">
          设为默认
        </button>
      </div>
      <div class="save-actions">
        <span>{{ isDirty ? '有未保存的修改' : '已保存' }}</span>
        <button
          type="button"
          class="secondary-button"
          :disabled="!canSave || settings.validating"
          :aria-busy="settings.validating || undefined"
          @click="settings.validateChatModel({ ...draft }, apiKey.trim())"
        >
          {{ settings.validating ? '测试中…' : '测试连接' }}
        </button>
        <button type="submit" class="primary-button" :disabled="!canSave || settings.saving" :aria-busy="settings.saving || undefined">
          {{ settings.saving ? '保存中…' : '保存配置' }}
        </button>
      </div>
    </footer>
  </form>
</template>
<style scoped lang="scss">
@use '@/styles/model-editor';
</style>
