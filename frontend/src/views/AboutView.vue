<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Link, Message } from '@element-plus/icons-vue'
import { http } from '@/api/client'

const name = ref('Canteen Recommendation Agent')
const title = ref('食堂菜品推荐与营养分析 Agent')
const version = ref('--')
const backendOk = ref(false)

const features = [
  { e: '🍽️', t: '菜品查询', d: '按菜名查热量/蛋白/碳水/脂肪与来源' },
  { e: '💰', t: '智能推荐', d: '按预算、口味、忌口推荐一餐' },
  { e: '🧮', t: '组合优化', d: '子 Agent 求解最优一餐搭配' },
  { e: '📝', t: '饮食记录', d: '手工 + 聊天记录联动，HITL 确认' },
  { e: '📊', t: '营养趋势', d: '热量与三大营养素图表 + 日均对照' },
  { e: '🌦️', t: '天气推荐', d: '按天气温度推荐热汤或清淡菜' },
  { e: '🍲', t: '自定义菜品', d: '保存常用菜品，快捷录入营养' },
  { e: '⚙️', t: '后台管理', d: '菜品/用户/Token 用量运营管理' },
]

const techs = ['FastAPI', 'LangChain', 'SQLite', 'Chroma RAG', 'Vue3', 'Element Plus', 'ECharts', 'Docker']

onMounted(async () => {
  try {
    const { data } = await http.get('/health')
    name.value = data.name || name.value
    title.value = data.title || title.value
    version.value = data.version || '--'
    backendOk.value = true
  } catch {
    backendOk.value = false
  }
})
</script>

<template>
  <div class="about-page">
    <el-card shadow="never" class="about-card">
      <div class="about-hero">
        <div class="about-logo">🍚</div>
        <h1 class="about-title">{{ title }}</h1>
        <p class="about-desc">
          智能食堂点餐参谋：用自然语言查菜品营养、按预算推荐一餐、记录每日摄入，
          并用趋势图洞察营养变化。
        </p>
        <div class="about-meta">
          <el-tag size="large" effect="plain" class="meta-tag">{{ name }} v{{ version }}</el-tag>
          <el-tag size="large" :type="backendOk ? 'success' : 'danger'" effect="light" class="meta-tag">
            {{ backendOk ? '服务运行中' : '后端未连接' }}
          </el-tag>
          <a
            class="meta-link"
            href="https://github.com/Jzy258/canteen-recommendation-agent"
            target="_blank"
            rel="noopener"
          >GitHub 仓库 ↗</a>
        </div>
      </div>

      <el-divider />

      <div class="about-section">
        <h2 class="section-title">✨ 主要功能</h2>
        <div class="feature-grid">
          <div v-for="f in features" :key="f.t" class="feature-card">
            <div class="feature-emoji">{{ f.e }}</div>
            <div class="feature-title">{{ f.t }}</div>
            <div class="feature-desc">{{ f.d }}</div>
          </div>
        </div>
      </div>

      <el-divider />

      <div class="about-section">
        <h2 class="section-title">🛠️ 技术栈</h2>
        <div class="tech-tags">
          <el-tag v-for="t in techs" :key="t" size="large" effect="plain" class="tech-tag">{{ t }}</el-tag>
        </div>
      </div>

      <el-divider />

      <div class="about-section">
        <h2 class="section-title">📬 联系方式</h2>
        <div class="contact-list">
          <a class="contact-item" href="mailto:ginna_238@qq.com">
            <el-icon class="contact-icon"><Message /></el-icon>
            <span>ginna_238@qq.com</span>
          </a>
          <a class="contact-item" href="https://github.com/Jzy258/canteen-recommendation-agent" target="_blank" rel="noopener">
            <el-icon class="contact-icon"><Link /></el-icon>
            <span>GitHub · Jzy258/canteen-recommendation-agent</span>
          </a>
        </div>
      </div>

      <div class="about-footer">
        食堂菜品推荐与营养分析 Agent · © 2026
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.about-page {
  max-width: 880px;
  width: 100%;
  box-sizing: border-box;
  margin: 0 auto;
  padding: 16px;
}
.about-card {
  border-radius: 16px;
}
.about-hero {
  text-align: center;
  padding: 20px 8px 8px;
}
.about-logo {
  font-size: 56px;
  line-height: 1;
}
.about-title {
  margin: 12px 0 6px;
  font-size: 26px;
  color: #303133;
}
.about-desc {
  margin: 0 auto 16px;
  max-width: 560px;
  color: #606266;
  font-size: 14px;
  line-height: 1.8;
}
.about-meta {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.meta-tag {
  border-radius: 999px;
}
.meta-link {
  color: var(--el-color-primary);
  text-decoration: none;
  font-size: 14px;
}
.meta-link:hover {
  text-decoration: underline;
}
.about-section {
  padding: 4px 4px 8px;
}
.section-title {
  font-size: 18px;
  color: #303133;
  margin: 0 0 14px;
}
.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}
.feature-card {
  border: 1px solid var(--el-color-primary-light-8);
  border-radius: 12px;
  padding: 14px 12px;
  text-align: center;
  background: #fff;
}
.feature-emoji {
  font-size: 28px;
}
.feature-title {
  margin-top: 6px;
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}
.feature-desc {
  margin-top: 4px;
  color: #909399;
  font-size: 12px;
  line-height: 1.6;
}
.tech-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.tech-tag {
  border-radius: 999px;
}
.about-footer {
  margin-top: 12px;
  text-align: center;
  color: #c0c4cc;
  font-size: 12px;
}
.contact-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 420px;
}
.contact-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
  text-decoration: none;
  padding: 8px 12px;
  border: 1px solid var(--el-color-primary-light-8);
  border-radius: 10px;
  transition: border-color 0.2s, color 0.2s;
}
.contact-item:hover {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}
.contact-icon {
  color: var(--el-color-primary);
}
/* ===== 移动端适配 ===== */
@media (max-width: 768px) {
  .about-page {
    padding: 10px;
  }
  .about-card {
    border-radius: 12px;
  }
  .about-meta {
    gap: 8px;
  }
  .about-logo {
    font-size: 44px;
  }
  .about-title {
    font-size: 22px;
  }
  .feature-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 10px;
  }
}
</style>
