import {
  App as AntdApp,
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Radio,
  Row,
  Select,
  Space,
  Steps,
  Switch,
  Tag,
  Typography,
} from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { audit } from '@/api'
import { getCountryRules, type CountryRule } from '@/api/platform'
import LogoUpload from '@/components/LogoUpload'
import type { AuditFormData } from '@/types/audit'

const { Paragraph, Text, Title } = Typography

const initialForm: AuditFormData = {
  brandName: '',
  englishName: '',
  niceClass: '',
  goodsServices: '',
  targetCountries: ['越南'],
  operationStage: 'pre-entry',
  plannedMarkets: 1,
  hasChinaBaseMark: false,
  logo: '',
}

const TARGET_COUNTRY_OPTIONS = ['越南', '泰国', '印尼', '马来西亚', '菲律宾', '新加坡'].map(
  (country) => ({ value: country, label: country }),
)

const COMMON_NICE_CLASSES = [
  '第43类-餐饮服务',
  '第25类-服装鞋帽',
  '第30类-方便食品',
  '第32类-啤酒饮料',
]

const NICE_CLASS_NAMES = [
  '化学原料',
  '颜料油漆',
  '日化用品',
  '燃料油脂',
  '医药用品',
  '金属材料',
  '机械设备',
  '手工器械',
  '科学仪器',
  '医疗器械',
  '灯具空调',
  '运输工具',
  '军火烟火',
  '珠宝钟表',
  '乐器',
  '办公用品',
  '橡胶制品',
  '皮革皮具',
  '建筑材料',
  '家具',
  '厨房洁具',
  '绳网袋篷',
  '纱线丝',
  '布料床单',
  '服装鞋帽',
  '钮扣拉链',
  '地毯席垫',
  '健身器材',
  '食品',
  '方便食品',
  '饲料种籽',
  '啤酒饮料',
  '酒',
  '烟草烟具',
  '广告销售',
  '金融物管',
  '建筑修理',
  '通讯服务',
  '运输贮藏',
  '材料加工',
  '教育娱乐',
  '网站服务',
  '餐饮服务',
  '医疗园艺',
  '法律服务',
]

export const NICE_CLASS_OPTIONS = NICE_CLASS_NAMES.map(
  (name, index) => `第${index + 1}类-${name}`,
)
  .sort((a, b) => {
    const aIndex = COMMON_NICE_CLASSES.indexOf(a)
    const bIndex = COMMON_NICE_CLASSES.indexOf(b)

    if (aIndex >= 0 && bIndex >= 0) return aIndex - bIndex
    if (aIndex >= 0) return -1
    if (bIndex >= 0) return 1

    return Number(a.match(/第(\d+)类/)?.[1] ?? 0) - Number(b.match(/第(\d+)类/)?.[1] ?? 0)
  })
  .map((value) => ({ value, label: value }))

function Submit() {
  const [form] = Form.useForm<AuditFormData>()
  const [submitLoading, setSubmitLoading] = useState(false)
  const [countryRules, setCountryRules] = useState<CountryRule[]>([])
  const navigate = useNavigate()
  const { message } = AntdApp.useApp()
  const selectedCountries = Form.useWatch('targetCountries', form) ?? initialForm.targetCountries

  useEffect(() => {
    getCountryRules()
      .then(setCountryRules)
      .catch(() => setCountryRules([]))
  }, [])

  const activeCountryRules = useMemo(
    () => countryRules.filter((rule) => selectedCountries?.includes(rule.country)),
    [countryRules, selectedCountries],
  )

  const fillDemo = () => {
    form.setFieldsValue({
      brandName: '墨兰奶白',
      englishName: 'Molan Tea',
      niceClass: '第43类-餐饮服务',
      goodsServices: '茶饮及餐饮门店服务，计划进入越南门店和外卖平台。',
      targetCountries: ['越南', '泰国'],
      operationStage: 'pre-entry',
      plannedMarkets: 3,
      hasChinaBaseMark: false,
    })
  }

  const handleFinish = async (values: AuditFormData) => {
    setSubmitLoading(true)

    try {
      const result = await audit({ ...values, logo: values.logo.trim() })
      message.success('M5 商标资料核验任务已提交')
      navigate('/reviewing', { state: { taskId: result.data.taskId } })
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '请检查后端服务是否启动'
      message.error(`提交失败：${errorMsg}`)
    } finally {
      setSubmitLoading(false)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <Space align="start" style={{ display: 'flex', justifyContent: 'space-between' }} wrap>
          <div>
            <Title level={2} style={{ marginBottom: 8 }}>
              M5 · 商标与技术出海资料核验（内测）
            </Title>
            <Paragraph type="secondary" style={{ fontSize: 15, marginBottom: 0 }}>
              该入口仅作为 M5 的商标资料核验子能力，输出风险线索与待补事实，不判断可注册性、侵权或申请结果。
            </Paragraph>
          </div>
          <Button onClick={fillDemo}>填入比赛演示案例</Button>
        </Space>
        <Steps
          current={0}
          items={[{ title: '填写资料' }, { title: '风险线索整理' }, { title: '人工复核报告' }]}
          size="small"
          style={{ marginTop: 18, maxWidth: 760 }}
        />
      </div>

      <Form<AuditFormData>
        form={form}
        initialValues={initialForm}
        layout="vertical"
        onFinish={handleFinish}
      >
        <Row gutter={[24, 24]}>
          <Col xs={24} xl={16}>
            <Card
              title="商标与权属基础信息"
              style={{ marginBottom: 24 }}
              styles={{ body: { paddingBottom: 8 } }}
            >
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item
                    label="品牌名称"
                    name="brandName"
                    rules={[
                      { required: true, message: '请输入品牌名称' },
                      { max: 50, message: '品牌名称不能超过 50 个字符' },
                    ]}
                  >
                    <Input placeholder="请输入品牌名称（支持中文/越南语）" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    label="品牌英文名称"
                    name="englishName"
                    rules={[
                      { required: true, message: '请输入品牌英文名称' },
                      { max: 100, message: '品牌英文名称不能超过 100 个字符' },
                      {
                        pattern: /^[a-zA-Z0-9\s\-&]+$/,
                        message: '仅允许字母、数字、空格、连字符和 &',
                      },
                    ]}
                  >
                    <Input placeholder="请输入品牌英文名称" />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                label="尼斯分类"
                name="niceClass"
                rules={[{ required: true, message: '请选择尼斯分类' }]}
              >
                <Select
                  showSearch
                  filterOption={(input, option) =>
                    String(option?.label ?? '')
                      .toLowerCase()
                      .includes(input.toLowerCase())
                  }
                  options={NICE_CLASS_OPTIONS}
                  placeholder="请选择尼斯分类"
                />
              </Form.Item>
            </Card>

            <Card
              title="目标市场与资料范围"
              style={{ marginBottom: 24 }}
              styles={{ body: { paddingBottom: 8 } }}
            >
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item
                    label="目标国家"
                    name="targetCountries"
                    rules={[{ required: true, message: '请选择至少一个目标国家' }]}
                  >
                    <Select
                      mode="multiple"
                      options={TARGET_COUNTRY_OPTIONS}
                      placeholder="请选择目标国家"
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item label="计划覆盖市场数" name="plannedMarkets">
                    <InputNumber min={1} max={10} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col xs={24} md={16}>
                  <Form.Item label="当前业务阶段" name="operationStage">
                    <Radio.Group
                      optionType="button"
                      buttonStyle="solid"
                      options={[
                        { value: 'pre-entry', label: '申请前资料核验' },
                        { value: 'launching', label: '申请中材料整理' },
                        { value: 'operating', label: '运营中权利维护' },
                      ]}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="已有中国基础标" name="hasChinaBaseMark" valuePropName="checked">
                    <Switch checkedChildren="有" unCheckedChildren="无" />
                  </Form.Item>
                </Col>
              </Row>
            </Card>

            <Card title="商标、商品服务与权属资料">
              <Form.Item
                label="商品/服务描述"
                name="goodsServices"
                rules={[
                  { required: true, message: '请输入商品/服务描述' },
                  { max: 500, message: '商品/服务描述不能超过 500 个字符' },
                ]}
              >
                <Input.TextArea
                  maxLength={500}
                  placeholder="请描述品牌主营业务、目标市场、出海计划等"
                  rows={4}
                  showCount
                />
              </Form.Item>

              <Form.Item
                label="品牌 Logo"
                name="logo"
                rules={[{ required: true, message: '请上传品牌 Logo' }]}
              >
                <LogoUpload />
              </Form.Item>
            </Card>
          </Col>
          <Col xs={24} xl={8}>
            <Card title="目标国 M5 核验提示">
              {activeCountryRules.length ? (
                <Space direction="vertical" size={16} style={{ display: 'flex' }}>
                  {activeCountryRules.map((rule) => (
                    <div className="country-rule" key={rule.country}>
                      <Space align="start" direction="vertical" size={8}>
                        <Text strong>{rule.country}</Text>
                        <Paragraph type="secondary">{rule.reviewFocus}</Paragraph>
                        <Space size={[6, 6]} wrap>
                          {rule.riskTags.map((tag) => (
                            <Tag color="blue" key={tag}>{tag}</Tag>
                          ))}
                        </Space>
                        <Text type="secondary">{rule.legalBasis}</Text>
                      </Space>
                    </div>
                  ))}
                </Space>
              ) : (
                <Paragraph type="secondary">
                  选择目标国家后，将展示仅供初步参考的资料线索；具体适用性、版本和权属须人工复核。
                </Paragraph>
              )}
            </Card>
          </Col>
        </Row>

        <div style={{ marginTop: 24, textAlign: 'right' }}>
          <Space>
            <Button onClick={() => form.resetFields()}>重置</Button>
            <Button htmlType="submit" loading={submitLoading} type="primary">
              提交资料核验
            </Button>
          </Space>
        </div>
      </Form>
    </div>
  )
}

export default Submit
