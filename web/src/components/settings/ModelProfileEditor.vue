<script setup lang="ts">
import { toRefs, type UnwrapNestedRefs } from 'vue'
import type { useModelSettings } from '@/composables/useModelSettings'
import { MODEL_PROVIDERS, COMPATIBLE_PROVIDER_PRESETS } from '@/config/model-providers'
import IconSymbol from '@/components/common/IconSymbol.vue'
import ModelSelectionField from './ModelSelectionField.vue'
const props = defineProps<{ editor: UnwrapNestedRefs<ReturnType<typeof useModelSettings>> }>()
const {
  settings,
  draft,
  compatiblePreset,
  customService,
  provider,
  displayProviderName,
  apiKey,
  revealKey,
  endpointChanged,
  endpointHelp,
  requiresEndpoint,
  keyRequired,
  isDirty,
  canSave,
  modelCount,
  manualModelId,
  closeEditor,
  save,
  handleProviderChange,
  handlePresetChange,
  handleProtocolChange,
  remove,
} = toRefs(props.editor)
</script>

<template>
  <form class="profile-editor" @submit.prevent="save">
    <header class="editor-heading">
      <button type="button" class="back-button" :disabled="settings.saving" @click="closeEditor">{{ $t('‹ 返回模型列表') }}</button>
      <div class="editor-title">
        <span class="provider-mark" :class="draft.provider">{{
          customService ? '+' : compatiblePreset?.monogram || provider.monogram
        }}</span>
        <span
          ><small>{{ draft.id ? $t('编辑模型服务') : $t('添加模型服务') }}</small>
          <h3>{{ displayProviderName }}</h3></span
        >
        <i v-if="draft.isDefault" class="default-pill">{{ $t('默认') }}</i>
      </div>
    </header>

    <fieldset class="editor-body" :disabled="settings.saving">
      <label class="form-field">
        <span>{{ $t('服务名称') }}<b>{{ $t('必填') }}</b></span>
        <input
          v-model.trim="draft.name"
          data-testid="profile-name"
          maxlength="80"
          :placeholder="$t('服务名称')"
        />
      </label>

      <label v-if="customService" class="form-field">
        <span>{{ $t('接口协议') }}</span>
        <select data-testid="relay-protocol" :value="draft.provider" @change="handleProtocolChange">
          <option value="openai_compatible">OpenAI · Chat Completions</option>
          <option value="anthropic">Anthropic · Messages</option>
        </select>
      </label>

      <div class="form-field">
        <label for="model-base-url">{{ customService ? $t('中转站 / 网关地址') : $t(provider.baseUrlLabel) }} <b v-if="requiresEndpoint">{{ $t('必填') }}</b></label>
        <input
          id="model-base-url"
          v-model.trim="draft.baseUrl"
          data-testid="base-url"
          type="url"
          :required="requiresEndpoint"
          :placeholder="customService ? draft.provider === 'anthropic' ? 'https://gateway.example' : 'https://gateway.example/v1' : compatiblePreset?.baseUrl || $t(provider.baseUrlPlaceholder)"
        />
        <small>{{ endpointHelp }} <a v-if="compatiblePreset?.docsUrl && !customService" :href="compatiblePreset.docsUrl" target="_blank" rel="noopener noreferrer">{{ $t('查看服务文档 ↗') }}</a></small>
      </div>

      <label v-if="provider.apiKeyMode !== 'none'" class="form-field">
        <span
          >API Key <b>{{ keyRequired ? $t('必填') : $t('按需') }}</b></span
        >
        <span class="secret">
          <input
            v-model="apiKey"
            data-testid="api-key"
            :type="revealKey ? 'text' : 'password'"
            autocomplete="new-password"
            :placeholder="draft.credentialConfigured && !endpointChanged ? $t('已配置；留空继续使用') : $t('粘贴 API Key')"
          />
          <button
            type="button"
            :aria-label="revealKey ? $t('隐藏 API Key') : $t('显示 API Key')"
            @click="revealKey = !revealKey"
          >
            <IconSymbol :name="revealKey ? 'eye-off' : 'eye'" :size="16" />
          </button>
        </span>
        <small v-if="endpointChanged" class="warning"
          >{{ $t('服务地址或接口已更换，请重新填写 API Key。') }}</small
        >
        <small v-else-if="draft.credentialConfigured" class="credential-confirmed"
          ><i />{{ $t('密钥已保存') }}</small
        >
      </label>

      <ModelSelectionField :editor="editor" />

      <details v-if="!customService || draft.provider === 'openai_compatible'" class="custom-settings">
        <summary>
          <span><strong>{{ $t('自定义设置') }}</strong></span>
          <i>›</i>
        </summary>
        <div class="custom-settings-body">
          <label v-if="!customService" class="form-field">
            <span>{{ $t('接口类型') }}</span>
            <select data-testid="provider-type" :value="draft.provider" @change="handleProviderChange">
              <option v-for="item in MODEL_PROVIDERS" :key="item.id" :value="item.id">
                {{ $t(item.name) }}
              </option>
            </select>
          </label>
          <label v-if="draft.provider === 'openai_compatible'" class="form-field">
            <span>{{ $t('服务预设') }}</span>
            <select data-testid="preset-select" :value="compatiblePreset?.id || ''" @change="handlePresetChange">
              <option value="">{{ $t('自定义地址') }}</option>
              <option v-for="item in COMPATIBLE_PROVIDER_PRESETS" :key="item.id" :value="item.id">
                {{ $t(item.name) }}
              </option>
            </select>
          </label>
        </div>
      </details>

      <p v-if="settings.validation" class="validation" :class="{ ok: settings.validation.ok }">
        <IconSymbol :name="settings.validation.ok ? 'check' : 'alert'" :size="15" />{{ settings.validation.message }}
      </p>
    </fieldset>

    <footer class="editor-footer">
      <div>
        <button v-if="draft.id" type="button" class="danger-button" :disabled="settings.saving" @click="remove">{{ $t('删除服务') }}</button>
      </div>
      <div class="save-actions">
        <span>{{ isDirty ? $t('有未保存的修改') : $t('已保存') }}</span>
        <button
          type="button"
          class="secondary-button"
          :disabled="!canSave || settings.validating || settings.saving"
          :aria-busy="settings.validating || undefined"
          @click="settings.validateChatModel({ ...draft, model: draft.model || manualModelId.trim() }, apiKey.trim())"
        >
          {{ settings.validating ? $t('测试中…') : modelCount > 1 ? $t('测试首个模型') : $t('测试连接') }}
        </button>
        <button type="submit" class="primary-button" :disabled="!canSave || settings.saving" :aria-busy="settings.saving || undefined">
          {{ settings.saving ? $t('保存中…') : modelCount > 1 ? $t('保存 {0} 个模型', [modelCount]) : $t('保存配置') }}
        </button>
      </div>
    </footer>
  </form>
</template>
<style scoped lang="scss">
@use '@/styles/model-editor';
</style>
