import { motion } from 'motion/react'

interface RiskRadarProps {
  score: number
  title?: string
  subtitle?: string
}

const rings = [82, 124, 166, 208]

function RiskRadar({ score, title = 'AI Risk Radar', subtitle = 'Cross-class shield active' }: RiskRadarProps) {
  const normalized = Math.max(0, Math.min(score, 100))

  return (
    <div className="risk-radar" aria-label={`风险雷达评分 ${normalized}`}>
      <div className="radar-grid">
        {rings.map((size) => (
          <span key={size} style={{ height: size, width: size }} />
        ))}
        <i />
      </div>
      <motion.div
        animate={{ rotate: 360 }}
        className="radar-sweep"
        transition={{ duration: 7.5, ease: 'linear', repeat: Infinity }}
      />
      <motion.div
        animate={{ scale: [1, 1.12, 1], opacity: [0.85, 1, 0.85] }}
        className="radar-core"
        transition={{ duration: 2.8, ease: 'easeInOut', repeat: Infinity }}
      >
        <strong>{normalized}</strong>
        <span>risk score</span>
      </motion.div>
      <div className="radar-caption">
        <strong>{title}</strong>
        <span>{subtitle}</span>
      </div>
      <span className="radar-dot dot-a" />
      <span className="radar-dot dot-b" />
      <span className="radar-dot dot-c" />
    </div>
  )
}

export default RiskRadar
