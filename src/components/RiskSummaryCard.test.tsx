import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import RiskSummaryCard from '@/components/RiskSummaryCard'
import { createAuditResult } from '@/test/fixtures'
import { renderWithProviders } from '@/test/render'

describe('RiskSummaryCard', () => {
  it('同时展示风险文本、分值和人工复核状态', () => {
    renderWithProviders(<RiskSummaryCard data={createAuditResult()} />)

    expect(screen.getByText('墨兰奶白')).toBeInTheDocument()
    expect(screen.getByText('高危')).toBeInTheDocument()
    expect(screen.getByLabelText('风险分值 88，风险等级高危')).toBeInTheDocument()
    expect(screen.getByText('建议人工复核')).toBeInTheDocument()
  })
})
