import { Button } from 'antd'
import { Link, useNavigate } from 'react-router-dom'
import { assetPath } from '@/utils/assetPath'

export default function ExperienceQr() {
  const qrImage = assetPath('/teacher-experience-qr.png')
  const navigate = useNavigate()

  return (
    <section className="experience-qr" aria-label="东盟扫码体验入口">
      <Link className="experience-qr-image" to="/experience">
        <img alt="东盟跨境商事法律 AI 助手体验二维码" src={qrImage} width={120} height={120} />
      </Link>
      <div className="experience-qr-content">
        <strong>老师扫码体验 · 无需注册</strong>
        <p>手机扫码进入东盟体验页，也可在当前设备直接打开。</p>
        <Button block onClick={() => navigate('/experience')}>打开体验入口</Button>
        <a href={qrImage} download="东盟法律AI助手-体验二维码.png">下载二维码</a>
      </div>
    </section>
  )
}
