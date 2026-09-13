<template>
  <div v-if="isShowProgress" class="progress">
    <div>
      <QCircularProgress
        v-if="isDeterminate || backendProgress?.active"
        showValue
        :value="displayProgress"
        :min="0"
        :max="1"
        rounded
        font-size="12px"
        color="primary"
        size="xl"
        :thickness="0.3"
      >
        {{ formattedProgress }}%
      </QCircularProgress>
      <div v-if="backendProgress?.stage" class="q-mt-md">
        {{ backendProgress.stage }}
      </div>
      <QCircularProgress
        v-if="!isDeterminate && !backendProgress?.active"
        indeterminate
        color="primary"
        rounded
        :thickness="0.3"
        size="xl"
      />
      <div v-if="!backendProgress?.stage" class="q-mt-md">生成中です...</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import { useStore } from "@/store";
import { createEngineUrl } from "@/domain/url";

const store = useStore();

const progress = computed(() => store.getters.PROGRESS);
const activeEngineUrl = computed(() => {
  const activeAudioKey = store.getters.ACTIVE_AUDIO_KEY;
  const audioItem =
    activeAudioKey == undefined
      ? undefined
      : store.state.audioItems[activeAudioKey];
  const engineInfo =
    audioItem == undefined
      ? undefined
      : store.state.engineInfos[audioItem.voice.engineId];
  if (engineInfo == undefined) return undefined;
  return createEngineUrl({
    ...engineInfo,
    port: store.state.altPortInfos[engineInfo.uuid] ?? engineInfo.defaultPort,
  });
});
const backendProgress = ref<{
  active: boolean;
  percent: number;
  stage: string;
}>();
const isShowProgress = ref<boolean>(false);
const isDeterminate = ref<boolean>(false);

let timeoutId: ReturnType<typeof setTimeout>;
let backendPollTimer: ReturnType<typeof setInterval> | undefined;
let backendPollInFlight = false;

const pollBackendProgress = async () => {
  if (backendPollInFlight || activeEngineUrl.value == undefined) return;
  backendPollInFlight = true;
  try {
    const response = await fetch(`${activeEngineUrl.value}/irodori/settings`, {
      signal: AbortSignal.timeout(2000),
    });
    if (!response.ok) return;
    const result = (await response.json()) as {
      progress?: { active?: boolean; percent?: number; stage?: string };
    };
    if (
      result.progress?.active === true &&
      typeof result.progress.percent === "number" &&
      typeof result.progress.stage === "string"
    ) {
      backendProgress.value = {
        active: true,
        percent: Math.max(0, Math.min(100, result.progress.percent)),
        stage: result.progress.stage,
      };
    } else {
      backendProgress.value = undefined;
    }
  } catch {
    // Engine startup/restarts must not interrupt normal generation progress.
  } finally {
    backendPollInFlight = false;
  }
};

const startBackendPolling = () => {
  if (backendPollTimer != undefined) return;
  void pollBackendProgress();
  backendPollTimer = setInterval(() => void pollBackendProgress(), 500);
};

const stopBackendPolling = () => {
  if (backendPollTimer != undefined) clearInterval(backendPollTimer);
  backendPollTimer = undefined;
  backendProgress.value = undefined;
};

const deferredProgressStart = () => {
  // 3秒待ってから表示する
  timeoutId = setTimeout(() => {
    isShowProgress.value = true;
  }, 3000);
};

watch(progress, (newValue, oldValue) => {
  if (newValue === -1) {
    // → 非表示
    clearTimeout(timeoutId);
    isShowProgress.value = false;
    stopBackendPolling();
  } else if (oldValue === -1 && newValue <= 1) {
    // 非表示 → 処理中
    deferredProgressStart();
    isDeterminate.value = false;
    startBackendPolling();
  } else if (oldValue !== -1 && 0 < newValue) {
    // 処理中 → 処理中(0%より大きな値)
    // 0 < value <= 1の間のみ進捗を%で表示する
    isDeterminate.value = true;
  }
});

onUnmounted(() => {
  clearTimeout(timeoutId);
  stopBackendPolling();
});

const formattedProgress = computed(() =>
  (displayProgress.value * 100).toFixed(),
);
const displayProgress = computed(() =>
  backendProgress.value?.active === true
    ? backendProgress.value.percent / 100
    : progress.value,
);
</script>

<style lang="scss" scoped>
@use "@/styles/colors" as colors;

.progress {
  background-color: rgba(colors.$display-rgb, 0.15);
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  text-align: center;
  align-items: center;
  justify-content: center;

  > div {
    color: colors.$display;
    background: colors.$surface;
    width: 200px;
    border-radius: 6px;
    padding: 14px 48px;
  }
}
</style>
