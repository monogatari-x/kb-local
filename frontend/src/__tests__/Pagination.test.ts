import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Pagination from '../components/Pagination.vue'

describe('Pagination', () => {
  it('renders current page and total', () => {
    const w = mount(Pagination, {
      props: { page: 2, page_size: 10, total: 50 },
    })
    expect(w.text()).toContain('第 2 页')
    expect(w.text()).toContain('共 50 条')
  })

  it('disables prev on page 1', () => {
    const w = mount(Pagination, {
      props: { page: 1, page_size: 10, total: 50 },
    })
    expect(w.find('[data-testid="prev"]').attributes('disabled')).toBeDefined()
  })

  it('disables next on last page', () => {
    const w = mount(Pagination, {
      props: { page: 5, page_size: 10, total: 50 },
    })
    expect(w.find('[data-testid="next"]').attributes('disabled')).toBeDefined()
  })

  it('emits update:page with page+1 on next click', async () => {
    const w = mount(Pagination, {
      props: { page: 2, page_size: 10, total: 50 },
    })
    await w.find('[data-testid="next"]').trigger('click')
    expect(w.emitted('update:page')?.[0]).toEqual([3])
  })
})
