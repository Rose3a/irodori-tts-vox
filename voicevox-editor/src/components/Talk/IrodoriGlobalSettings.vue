<template>
  <section class="q-pa-md">
    <div class="text-subtitle1 q-mb-sm">Irodori-TTS</div>
    <div class="text-caption q-mb-sm">全行共通の生成設定</div>
    <template v-if="settings">
      <QSelect
        v-model="settings.backend"
        outlined
        dense
        label="エンジン"
        :options="backends"
        emitValue
        mapOptions
        :disable="locked"
        class="q-mb-sm"
      />
      <QSelect
        v-model="settings.model"
        outlined
        dense
        label="モデル（ファイル名 または Hugging Face repo_id）"
        :options="modelOptions"
        emit-value
        map-options
        use-input
        fill-input
        hide-selected
        new-value-mode="add-unique"
        hint="プリセットから選択、または .safetensors の絶対パスを入力"
        @new-value="setCustomModel"
        :disable="locked"
        class="q-mb-sm"
      >
        <template #option="scope">
          <QItem v-bind="scope.itemProps">
            <QItemSection>
              <QItemLabel>{{ scope.opt.label }}</QItemLabel>
              <QItemLabel caption>{{ scope.opt.description }}</QItemLabel>
            </QItemSection>
          </QItem>
        </template>
      </QSelect>
      <div v-if="modelInfo" class="text-caption q-mb-sm">
        {{ modelInfo.kind === "hf" ? "Hugging Face" : "ローカル" }} ·
        {{ modelInfo.flowParameterization }} · 既定
        {{ modelInfo.defaultSteps }} ステップ
        <span v-if="modelInfo.kind === 'hf' && !modelInfo.downloaded">
          （未ダウンロード: 適用時に取得します）
        </span>
      </div>
      <div v-if="licenseName" class="text-caption q-mb-sm">
        ライセンス:
        <a
          v-if="licenseUrl"
          :href="licenseUrl"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ licenseName }}
        </a>
        <span v-else>{{ licenseName }}</span>
      </div>
      <div v-if="modelInfo?.meanflow" class="text-caption q-mb-sm">
        MeanFlow モデル: ステップ数4が既定。ScheduleとCFGは未使用。
      </div>
      <QBtn
        color="primary"
        label="設定を適用"
        :loading="busy"
        :disable="locked"
        @click="apply"
      />
      <QBtn flat label="一覧を更新" :disable="locked" @click="refresh" />
      <div class="text-caption q-mt-sm">{{ status }}</div>
      <div v-if="progress.active" class="q-mt-sm">
        <QLinearProgress :value="progress.percent / 100" rounded />
        <div class="text-caption">
          {{ progress.percent }}% - {{ progress.stage }}
        </div>
      </div>
      <div class="row q-mt-sm">
        <QBtn
          flat
          dense
          label="モデルフォルダ"
          :disable="locked"
          @click="openFolder('models')"
        />
        <QBtn
          flat
          dense
          label="話者フォルダ"
          :disable="locked"
          @click="openFolder('speakers')"
        />
      </div>
      <QExpansionItem
        label="モデル・話者の追加 / セットアップ"
        dense
        class="q-mt-sm"
      >
        <div class="text-caption q-pa-sm" style="overflow-wrap: anywhere">
          <p>
            モデルフォルダ: {{ modelFolder }}<br />一覧内の
            .safetensors、または任意の .safetensors 絶対パスを指定できます。
          </p>
          <p>
            話者: {{ speakerFolder }}<br />*.speaker.safetensors
            を置いて一覧を更新します。
          </p>
          <p>
            切り替え後の初回生成時にモデルを読み込みます。前のエンジンは解放します。
          </p>
          <p>
            TensorRTはモデルに対応したGPU用plan、RadeonはDirectML環境が必要です。
          </p>
          <p>
            初回準備はエンジンフォルダの setup_venv.bat。配置手順は同梱の
            IRODORI_EDITOR.md を参照してください。
          </p>
        </div>
      </QExpansionItem>
    </template>
    <div v-if="error" role="alert" class="text-negative text-caption q-mt-sm">
      {{ error }}
    </div>
    <QBtn
      v-if="!settings"
      flat
      label="接続を再試行"
      :disable="locked"
      @click="refresh"
    />
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useStore } from "@/store";
import { createEngineUrl } from "@/domain/url";
import { clearAudioCache } from "@/store/audioGenerate";
import { IRODORI_DEFAULT_STEPS, irodoriDefaultSteps } from "@/domain/irodori";
import type { EngineId } from "@/type/preload";
const props = defineProps<{ engineId: EngineId }>();
const store = useStore();
const modelInfo = ref<ModelInfo>();
const defaultSteps = computed(
  () =>
    modelInfo.value?.defaultSteps ??
    irodoriDefaultSteps.value ??
    IRODORI_DEFAULT_STEPS,
);
type Settings = {
  backend: string;
  model: string;
  seed: number;
  sway_coeff: number;
};
type ModelInfo = {
  source: string;
  kind: "hf" | "local";
  resolved: string | null;
  downloaded: boolean;
  flowParameterization: string;
  meanflow: boolean;
  defaultSteps: number;
  metadataAvailable: boolean;
  license?: string;
  licenseUrl?: string;
};
type Status = {
  settings: Settings;
  loaded: boolean;
  modelFolder: string;
  speakerFolder: string;
  availableBackends: Record<string, boolean>;
  progress: { active: boolean; percent: number; stage: string };
  modelInfo?: ModelInfo;
};
const settings = ref<Settings>();
watch(defaultSteps, (value) => {
  irodoriDefaultSteps.value = value;
});
const modelFolder = ref("");
const speakerFolder = ref("");
const status = ref("");
const error = ref("");
const busy = ref(false);
const progress = ref<Status["progress"]>({
  active: false,
  percent: 0,
  stage: "idle",
});
// オプション自身が持つロックを除き、生成中や他の処理中は変更を防ぐ。
const locked = computed(
  () =>
    busy.value ||
    store.state.uiLockCount > (store.state.isSettingDialogOpen ? 1 : 0),
);
const backendDefinitions = [
  { label: "CPU / PyTorch", value: "cpu" },
  { label: "NVIDIA / CUDA", value: "cuda" },
  { label: "NVIDIA / TensorRT", value: "trt" },
  { label: "AMD / DirectML", value: "radeon" },
];
const availableBackends = ref<Record<string, boolean>>({ cpu: true });
const backends = computed(() =>
  backendDefinitions.filter(
    (item) => availableBackends.value[item.value] === true,
  ),
);
const modelOptions = [
  {
    label: "Irodori-TTS v4.1 Small（既定・8ステップ）",
    value: "Aratako/Irodori-TTS-v4.1-Small",
    description: "RFモデル / MIT",
  },
  {
    label: "Irodori-TTS v4.1 Small MF（4ステップ）",
    value: "Aratako/Irodori-TTS-v4.1-Small-MF",
    description: "MeanFlowモデル / MIT",
  },
  {
    label: "Irodori-TTS v4.1 Anime（8ステップ）",
    value: "phasefield-audio/Irodori-TTS-v4.1-Anime",
    description: "Anime fine-tune / MIT",
  },
];
const licenseName = computed(
  () =>
    modelInfo.value?.license ??
    (modelOptions.some((option) => option.value === settings.value?.model)
      ? "MIT"
      : undefined),
);
const licenseUrl = computed(
  () =>
    modelInfo.value?.licenseUrl ??
    (settings.value?.model.includes("/")
      ? `https://huggingface.co/${settings.value.model}`
      : undefined),
);
function setCustomModel(
  value: string,
  done: (value: string, mode?: "add" | "add-unique" | "toggle") => void,
) {
  const trimmed = value.trim();
  if (trimmed) done(trimmed, "add-unique");
}
const endpoint = computed(() => {
  const info = store.state.engineInfos[props.engineId];
  return createEngineUrl({
    ...info,
    port: store.state.altPortInfos[props.engineId] ?? info.defaultPort,
  });
});
let sessionToken: string | undefined;
async function authHeaders(json = false): Promise<Record<string, string>> {
  if (!sessionToken) {
    const response = await fetch(endpoint.value + "/irodori/session", {
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new Error("engine session unavailable");
    sessionToken = ((await response.json()) as { token: string }).token;
  }
  return {
    ...(json ? { "Content-Type": "application/json" } : {}),
    "X-Irodori-Session": sessionToken,
  };
}

async function request(path: string, value?: Settings): Promise<Status> {
  const headers = await authHeaders(Boolean(value));
  const response = await fetch(endpoint.value + path, {
    method: value ? "POST" : "GET",
    headers,
    body: value ? JSON.stringify(value) : undefined,
    signal: AbortSignal.timeout(30000),
  });
  if (!response.ok) {
    throw new Error(
      `設定の通信に失敗しました (${response.status}): ${await response.text()}`,
    );
  }
  return response.json() as Promise<Status>;
}

async function openFolder(folder: "models" | "speakers") {
  try {
    const response = await fetch(`${endpoint.value}/irodori/open-${folder}`, {
      method: "POST",
      headers: await authHeaders(),
    });
    if (!response.ok) throw new Error("フォルダを開けませんでした");
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause);
  }
}

async function run(save: boolean, refreshSpeakers = false) {
  if (busy.value) return;
  busy.value = true;
  store.mutations.LOCK_UI();
  error.value = "";
  try {
    const result = await request(
      "/irodori/settings",
      save ? settings.value : undefined,
    );
    settings.value = result.settings;
    progress.value = result.progress;
    modelInfo.value = result.modelInfo ?? modelInfo.value;
    availableBackends.value = result.availableBackends ?? { cpu: true };
    modelFolder.value = result.modelFolder;
    speakerFolder.value = result.speakerFolder;
    if (refreshSpeakers) {
      const response = await fetch(endpoint.value + "/refresh", {
        headers: await authHeaders(),
        signal: AbortSignal.timeout(30000),
      });
      if (!response.ok) throw new Error("話者一覧の更新に失敗しました");
      await store.actions.LOAD_CHARACTER({ engineId: props.engineId });
    }
    if (save || refreshSpeakers) clearAudioCache();
    status.value = result.loaded
      ? "モデル読込済み"
      : "準備OK · 初回生成時にモデルを読み込みます";
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    busy.value = false;
    store.mutations.UNLOCK_UI();
  }
}
async function pollStatus() {
  if (busy.value) return;
  try {
    const result = await request("/irodori/settings");
    progress.value = result.progress;
    if (result.modelInfo) modelInfo.value = result.modelInfo;
  } catch {
    // The engine can be restarting while the editor remains open.
  }
}
const apply = () => run(true);
const refresh = () => run(false, true);
let pollTimer: ReturnType<typeof setInterval> | undefined;
onMounted(() => {
  pollTimer = setInterval(() => void pollStatus(), 1500);
});
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
});
watch(
  () => props.engineId,
  () => {
    sessionToken = undefined;
    settings.value = undefined;
    void run(false);
  },
  { immediate: true },
);
</script>
