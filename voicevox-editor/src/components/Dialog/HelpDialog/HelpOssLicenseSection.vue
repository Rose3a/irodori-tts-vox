<template>
  <div v-if="detailIndex == undefined" class="container">
    <BaseScrollArea>
      <div class="inner inner-list">
        <h1 class="title">ライセンス情報</h1>
        <div class="list">
          <BaseRowCard
            v-for="(license, index) in props.licenses"
            :key="index"
            :title="
              license.name + (license.version ? ' | ' + license.version : '')
            "
            :description="license.license ?? undefined"
            clickable
            @click="selectLicenseIndex(index)"
          >
            <!-- 暫定でq-iconを使用 -->
            <QIcon name="keyboard_arrow_right" size="sm" />
          </BaseRowCard>
        </div>
      </div>
    </BaseScrollArea>
  </div>
  <div v-else class="container">
    <BaseScrollArea>
      <div class="inner">
        <div>
          <BaseButton
            label="戻る"
            icon="keyboard_arrow_left"
            @click="selectLicenseIndex(undefined)"
          />
        </div>
        <h1 class="title">{{ licenses[detailIndex].name }}</h1>
        <p v-if="licenses[detailIndex].license" class="license-name">
          ライセンス: {{ licenses[detailIndex].license }}
        </p>
        <a
          v-if="licenses[detailIndex].url"
          class="license-link"
          :href="licenses[detailIndex].url"
          target="_blank"
          rel="noopener noreferrer"
        >
          公式ライセンス
        </a>
        <pre>{{ licenses[detailIndex].text }}</pre>
      </div>
    </BaseScrollArea>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import BaseRowCard from "@/components/Base/BaseRowCard.vue";
import BaseButton from "@/components/Base/BaseButton.vue";
import BaseScrollArea from "@/components/Base/BaseScrollArea.vue";
import type { OssLicenseInfo } from "@/domain/staticAssets";

const props = defineProps<{
  licenses: OssLicenseInfo[];
}>();

const detailIndex = ref<number | undefined>(undefined);

const selectLicenseIndex = (index: number | undefined) => {
  detailIndex.value = index;
};
</script>

<style scoped lang="scss">
@use "@/styles/v2/variables" as vars;
@use "@/styles/v2/mixin" as mixin;
@use "@/styles/v2/colors" as colors;

.container {
  height: 100%;
}

.inner {
  display: flex;
  flex-direction: column;
  padding: vars.$padding-2;
  gap: vars.$gap-1;
  max-width: 960px;
  margin: auto;
}

.title {
  @include mixin.headline-1;
}

.license-name {
  margin: 0;
  color: colors.$display-sub;
}

.license-link {
  color: colors.$display-link;
}

.list {
  display: flex;
  flex-direction: column;
  gap: vars.$gap-1;
}

pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
