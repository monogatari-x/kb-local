import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScoreBadge from '../components/ScoreBadge.vue'

describe('ScoreBadge', () => {
  it('uses score-high class when score >= 0.7', () => {
    const w = mount(ScoreBadge, { props: { score: 0.85 } })
    expect(w.classes()).toContain('score-high')
    expect(w.text()).toContain('0.850')
  })

  it('uses score-mid class when 0.4 <= score < 0.7', () => {
    const w = mount(ScoreBadge, { props: { score: 0.5 } })
    expect(w.classes()).toContain('score-mid')
  })

  it('uses score-low class when score < 0.4', () => {
    const w = mount(ScoreBadge, { props: { score: 0.2 } })
    expect(w.classes()).toContain('score-low')
  })
})
