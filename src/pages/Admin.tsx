import {
  BarChartOutlined,
  CloudServerOutlined,
  LogoutOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import {
  App as AntdApp,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
  Progress,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd'
import type { TableColumnsType } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getAdminStatistics,
  getAdminSystemStatus,
  getAdminTaskDetail,
  getAdminTasks,
  getAdminUsers,
  type AdminStatistics,
  type AdminSystemStatus,
  type AdminTask,
  type AdminTaskDetail,
  type AdminUser,
} from '@/api/admin'
import { useAuth } from '@/context/AuthContext'
import { createLegalPassage, getLegalPassages, getSourcesForReview, reviewLegalSource, type LegalPassage, type LegalSource } from '@/api/legal'

const { Link, Paragraph, Text, Title } = Typography

const riskColor = {
  high: 'red',
  medium: 'orange',
  low: 'green',
  '': 'default',
} as const

const statusText = {
  pending: '等待中',
  processing: '审查中',
  done: '已完成',
  error: '失败',
} as const

function Admin() {
  const navigate = useNavigate()
  const { message } = AntdApp.useApp()
  const { user, logout } = useAuth()
  const [statistics, setStatistics] = useState<AdminStatistics | null>(null)
  const [tasks, setTasks] = useState<AdminTask[]>([])
  const [users, setUsers] = useState<AdminUser[]>([])
  const [systemStatus, setSystemStatus] = useState<AdminSystemStatus | null>(null)
  const [detail, setDetail] = useState<AdminTaskDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [legalSources, setLegalSources] = useState<LegalSource[]>([])
  const [legalSourceDetail, setLegalSourceDetail] = useState<LegalSource | null>(null)
  const [legalPassages, setLegalPassages] = useState<LegalPassage[]>([])
  const [passageSource, setPassageSource] = useState<LegalSource | null>(null)
  const [passageSaving, setPassageSaving] = useState(false)
  const [passageForm] = Form.useForm<{ locator: string; original_text: string; chinese_text?: string }>()

  const load = async () => {
    setLoading(true)
    try {
      const [nextStatistics, nextTasks, nextUsers, nextSystemStatus] = await Promise.all([
        getAdminStatistics(),
        getAdminTasks(),
        getAdminUsers(),
        getAdminSystemStatus(),
      ])
      setStatistics(nextStatistics)
      setTasks(nextTasks)
      setUsers(nextUsers)
      setSystemStatus(nextSystemStatus)
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '后台数据加载失败'
      message.error(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    getSourcesForReview().then(setLegalSources).catch(() => undefined)
  }, [])

  const reviewSource = async (sourceId: string, status: 'approved' | 'retired') => { await reviewLegalSource(sourceId, status); setLegalSources((items) => items.filter((item) => item.source_id !== sourceId)); message.success(status === 'approved' ? '资料和已录入的原文摘录均已通过审核' : '资料已退役') }

  const openLegalSourceDetail = async (source: LegalSource) => {
    setLegalSourceDetail(source)
    try { setLegalPassages(await getLegalPassages(source.source_id)) } catch { setLegalPassages([]) }
  }

  const submitPassage = async () => {
    if (!passageSource) return
    const values = await passageForm.validateFields()
    setPassageSaving(true)
    try {
      await createLegalPassage(passageSource.source_id, {
        source_id: passageSource.source_id,
        locator: values.locator,
        original_text: values.original_text,
        chinese_text: values.chinese_text || null,
        effective_at: null,
        prerequisites: passageSource.prerequisites,
        non_inferences: passageSource.non_inferences,
        approval_status: 'draft',
      })
      message.success('条款摘录已录入，资料通过时会一并确认。')
      passageForm.resetFields()
      setPassageSource(null)
      if (legalSourceDetail?.source_id === passageSource.source_id) setLegalPassages(await getLegalPassages(passageSource.source_id))
    } catch (error) { message.error(error instanceof Error ? error.message : '条款摘录保存失败') }
    finally { setPassageSaving(false) }
  }

  const openDetail = async (taskId: string) => {
    setDetailLoading(true)
    try {
      setDetail(await getAdminTaskDetail(taskId))
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '任务详情加载失败'
      message.error(errorMsg)
    } finally {
      setDetailLoading(false)
    }
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const columns: TableColumnsType<AdminTask> = [
    {
      title: '品牌',
      dataIndex: 'brandName',
      key: 'brandName',
      render: (value: string, record) => (
        <Space direction="vertical" size={2}>
          <Text strong>{value || '未命名品牌'}</Text>
          <Text type="secondary">{record.niceClass || '未选择类别'}</Text>
        </Space>
      ),
    },
    {
      title: '目标国家',
      dataIndex: 'targetCountries',
      key: 'targetCountries',
      render: (countries: string[]) => (
        <Space size={[4, 4]} wrap>
          {(countries || []).map((country, index) => <Tag key={`${country}-${index}`}>{country}</Tag>)}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (value: AdminTask['status']) => <Tag color={value === 'done' ? 'green' : value === 'error' ? 'red' : 'blue'}>{statusText[value]}</Tag>,
    },
    {
      title: '风险',
      dataIndex: 'riskLevel',
      key: 'riskLevel',
      render: (value: AdminTask['riskLevel'], record) => (
        <Space direction="vertical" size={2}>
          <Tag color={riskColor[value]}>{value ? value.toUpperCase() : 'N/A'}</Tag>
          <Progress percent={record.riskScore || 0} size="small" />
        </Space>
      ),
    },
    {
      title: '更新时间',
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      render: (value: string) => new Date(value).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button onClick={() => openDetail(record.taskId)} size="small">
            详情
          </Button>
          <Button onClick={() => navigate(`/report/${record.taskId}`)} size="small" type="link">
            报告
          </Button>
        </Space>
      ),
    },
  ]

  const userColumns: TableColumnsType<AdminUser> = [
    { title: '账号', dataIndex: 'username', key: 'username', render: (value: string) => <Text strong>{value}</Text> },
    { title: '角色', dataIndex: 'role', key: 'role', render: (value: AdminUser['role']) => <Tag color={value === 'superadmin' ? 'gold' : 'blue'}>{value === 'superadmin' ? '超级管理员' : '普通用户'}</Tag> },
    { title: '企业/团队', dataIndex: 'company', key: 'company' },
    { title: '活跃会话', dataIndex: 'activeSessions', key: 'activeSessions', align: 'center' },
    { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', render: (value: string) => new Date(value).toLocaleString() },
  ]

  return (
    <div className="admin-shell">
      <div className="admin-header">
        <div>
          <Title level={2}>超级管理员控制台</Title>
          <Paragraph type="secondary">
            超级管理员 {user?.username} 正在查看审查任务、风险分布、用户与系统运行状态。
          </Paragraph>
        </div>
        <Space wrap>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={load}>
            刷新
          </Button>
          <Button icon={<LogoutOutlined />} onClick={handleLogout}>
            退出登录
          </Button>
        </Space>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="总任务" value={statistics?.totalTasks ?? 0} prefix={<BarChartOutlined />} />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="高风险拦截" value={statistics?.highRiskBlocked ?? 0} prefix={<WarningOutlined />} />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="审查完成" value={statistics?.auditedBrands ?? 0} prefix={<SafetyCertificateOutlined />} />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="注册用户" value={statistics?.registeredUsers ?? 0} prefix={<TeamOutlined />} />
          </Card>
        </Col>
      </Row>

      <Card
        title="系统运行状态"
        style={{ marginTop: 24 }}
        extra={<Tag color={systemStatus?.database === 'online' ? 'green' : 'default'}>{systemStatus?.database === 'online' ? '数据库在线' : '检查中'}</Tag>}
      >
        <Descriptions
          column={{ xs: 1, sm: 2, lg: 4 }}
          items={[
            { key: 'database', label: '数据服务', children: <Space><CloudServerOutlined />SQLite 在线</Space> },
            { key: 'sessions', label: '活跃会话', children: systemStatus?.activeSessions ?? 0 },
            { key: 'processing', label: '待处理任务', children: systemStatus?.taskStatus.processing ?? 0 },
            { key: 'checked', label: '最近巡检', children: systemStatus ? new Date(systemStatus.checkedAt).toLocaleString() : '—' },
          ]}
        />
      </Card>

      <Card
        title="AI / RAG 就绪状态"
        style={{ marginTop: 24 }}
        extra={
          <Tag color={systemStatus?.legalKnowledge.ragReady ? 'green' : 'orange'}>
            {systemStatus?.legalKnowledge.ragReady ? 'RAG 已就绪' : 'RAG 待完成资料审核'}
          </Tag>
        }
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} md={6}>
            <Statistic
              title="模型服务"
              value={systemStatus?.ai.configured ? '已配置' : '未配置'}
              prefix={<CloudServerOutlined />}
            />
            <Text type="secondary">
              {systemStatus?.ai.configured
                ? `${systemStatus.ai.provider} · ${systemStatus.ai.model}`
                : '请配置 backend/.env'}
            </Text>
          </Col>
          <Col xs={12} md={6}>
            <Statistic title="待审核资料" value={systemStatus?.legalKnowledge.draftSources ?? 0} />
          </Col>
          <Col xs={12} md={6}>
            <Statistic title="已审核资料" value={systemStatus?.legalKnowledge.approvedSources ?? 0} />
          </Col>
          <Col xs={12} md={6}>
            <Statistic title="已审核原文摘录" value={systemStatus?.legalKnowledge.approvedPassages ?? 0} />
          </Col>
        </Row>
        {!systemStatus?.legalKnowledge.ragReady ? (
          <Paragraph type="warning" style={{ margin: '16px 0 0' }}>
            模型密钥与法律资料审核是两道独立门槛。只有资料及原文摘录经管理员确认后，
            才会进入受控 RAG；未审核资料不会被模型引用。
          </Paragraph>
        ) : null}
      </Card>

      <Card
        title="审查任务管理"
        style={{ marginTop: 24 }}
        extra={<Text type="secondary">共 {tasks.length} 条</Text>}
      >
        {tasks.length ? (
          <Table<AdminTask>
            columns={columns}
            dataSource={tasks}
            loading={loading}
            pagination={{ pageSize: 8 }}
            rowKey="taskId"
            scroll={{ x: 960 }}
          />
        ) : (
          <Empty description="暂无审查任务" />
        )}
      </Card>

      <Card title="法律资料审核" style={{ marginTop: 24 }} extra={<Text type="secondary">通过后才可进入检索与问答</Text>}>
        <Table<LegalSource> dataSource={legalSources} rowKey="source_id" pagination={{ pageSize: 6 }} scroll={{ x: 960 }} columns={[
          { title:'国家/模块', key:'scope', render:(_,r)=><Space><Tag>{r.country_code}</Tag><Tag>{r.legal_module}</Tag><Tag color={r.evidence_level==='A'?'green':'gold'}>{r.evidence_level}级</Tag></Space> },
          { title:'资料', dataIndex:'title', key:'title', render:(v:string,r)=><Space direction="vertical" size={2}><Text strong>{v}</Text><Text type="secondary">{r.supported_fact}</Text></Space> },
          { title:'核验', dataIndex:'verified_at', key:'verified_at' },
          { title:'操作', key:'action', render:(_,r)=><Space><Button size="small" onClick={()=>void openLegalSourceDetail(r)}>核验详情</Button><Tooltip title={r.reviewable_passage_count > 0 ? '点击后将一并确认已录入的原文摘录' : '我正在补录该资料的官方原文摘录，补齐后才可通过'}><Button size="small" type="primary" disabled={r.reviewable_passage_count === 0} onClick={()=>void reviewSource(r.source_id,'approved')}>{r.reviewable_passage_count > 0 ? '通过（确认摘录）' : '待补原文'}</Button></Tooltip><Button size="small" danger onClick={()=>void reviewSource(r.source_id,'retired')}>退役</Button></Space> },
        ]} />
      </Card>

      <Card
        title="用户与权限"
        style={{ marginTop: 24 }}
        extra={<Text type="secondary">仅超级管理员可访问</Text>}
      >
        <Table<AdminUser>
          columns={userColumns}
          dataSource={users}
          loading={loading}
          pagination={{ pageSize: 8 }}
          rowKey="userId"
          scroll={{ x: 860 }}
        />
      </Card>

      <Drawer
        open={Boolean(detail)}
        onClose={() => setDetail(null)}
        title="任务详情"
        width={620}
      >
        {detailLoading || !detail ? (
          <Empty description="正在加载任务详情" />
        ) : (
          <Space direction="vertical" size={18} style={{ display: 'flex' }}>
            <Descriptions
              column={1}
              bordered
              items={[
                { key: 'id', label: '任务 ID', children: detail.task_id },
                { key: 'status', label: '状态', children: detail.status },
                { key: 'progress', label: '进度', children: `${detail.progress}%` },
                { key: 'created', label: '创建时间', children: new Date(detail.created_at).toLocaleString() },
                { key: 'updated', label: '更新时间', children: new Date(detail.updated_at).toLocaleString() },
              ]}
            />
            <Card size="small" title="提交信息">
              <pre className="json-preview">{JSON.stringify(detail.request, null, 2)}</pre>
            </Card>
            <Card size="small" title="审查结果">
              {detail.result ? (
                <pre className="json-preview">{JSON.stringify(detail.result, null, 2)}</pre>
              ) : (
                <Empty description="暂无结果" />
              )}
            </Card>
          </Space>
        )}
      </Drawer>

      <Drawer
        open={Boolean(legalSourceDetail)}
        onClose={() => setLegalSourceDetail(null)}
        title="法律资料核验详情"
        width={680}
      >
        {legalSourceDetail && (
          <Space direction="vertical" size={16} style={{ display: 'flex' }}>
            <Descriptions
              column={1}
              bordered
              items={[
                { key:'scope', label:'适用范围', children:<Space><Tag>{legalSourceDetail.country_code}</Tag><Tag>{legalSourceDetail.legal_module}</Tag></Space> },
                { key:'title', label:'资料名称', children:legalSourceDetail.title },
                { key:'fact', label:'可支持的有限事实', children:legalSourceDetail.supported_fact },
                { key:'verified', label:'最近核验', children:legalSourceDetail.verified_at },
                { key:'source', label:'主资料链接', children:<Link href={legalSourceDetail.source_url} target="_blank">打开主资料</Link> },
                { key:'pre', label:'适用前提', children:legalSourceDetail.prerequisites.join('；') },
                { key:'non', label:'不能推断', children:legalSourceDetail.non_inferences.join('；') },
                { key:'review', label:'人工复核触发', children:legalSourceDetail.review_triggers.join('；') },
              ]}
            />
            <Card size="small" title="来源溯源（审核前逐项打开核对）">
              <Space direction="vertical" size={12} style={{ display: 'flex' }}>
                {legalSourceDetail.provenance.map((item) => (
                  <div key={item.provenance_id}>
                    <Space wrap><Tag color={item.role === 'primary' ? 'blue' : 'gold'}>{item.role === 'primary' ? '主来源' : '交叉核验'}</Tag><Text strong>{item.publisher}</Text></Space>
                    <div><Text type="secondary">{item.source_type} · {item.source_language} · 核验 {item.checked_at}</Text></div>
                    <Link href={item.source_url} target="_blank">打开来源</Link>
                    {item.version_note && <div><Text type="secondary">版本说明：{item.version_note}</Text></div>}
                    {item.conflict_note && <div><Text type="danger">待处理冲突：{item.conflict_note}</Text></div>}
                  </div>
                ))}
              </Space>
            </Card>
            <Card
              size="small"
              title="原文条款 / 章节摘录"
              extra={<Button size="small" type="primary" onClick={() => { passageForm.resetFields(); setPassageSource(legalSourceDetail) }}>录入摘录</Button>}
            >
              {legalPassages.length ? <Space direction="vertical" size={12} style={{ display:'flex' }}>
                {legalPassages.map((passage) => <div key={passage.passage_id}>
                  <Space wrap><Tag color={passage.approval_status === 'approved' ? 'green' : 'gold'}>{passage.approval_status === 'approved' ? '已审摘录' : '待审摘录'}</Tag><Text strong>{passage.locator}</Text></Space>
                  <Paragraph style={{ whiteSpace:'pre-wrap', margin:'6px 0' }} ellipsis={{ rows:4, expandable:true }}>{passage.original_text}</Paragraph>
                  {passage.chinese_text && <Text type="secondary">中文工作译文：{passage.chinese_text}</Text>}
                </div>)}
              </Space> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚未录入条款摘录" />}
            </Card>
            <Text type="warning">流程：我负责录入并交叉核验原文；你核对资料详情后，只需点击一次“通过（确认摘录）”。</Text>
          </Space>
        )}
      </Drawer>

      <Modal
        open={Boolean(passageSource)}
        title="录入法规原文条款 / 章节摘录"
        okText="保存为待审"
        cancelText="取消"
        confirmLoading={passageSaving}
        onCancel={() => setPassageSource(null)}
        onOk={() => void submitPassage()}
      >
        <Paragraph type="secondary">仅录入已从主来源核对的原文；不要自行概括或补全。保存后会在资料通过时一并确认。</Paragraph>
        <Form form={passageForm} layout="vertical">
          <Form.Item name="locator" label="条款 / 章节定位" rules={[{ required:true, message:'请填写例如 Article 12 / Chapter III' }]}>
            <Input placeholder="例如：Article 12 / Chapter III" />
          </Form.Item>
          <Form.Item name="original_text" label="原文摘录" rules={[{ required:true, message:'请粘贴经核对的法规原文' }]}>
            <Input.TextArea rows={8} placeholder="粘贴原文，不要改写" />
          </Form.Item>
          <Form.Item name="chinese_text" label="中文工作译文（可选）">
            <Input.TextArea rows={4} placeholder="仅作辅助阅读，原文为审核依据" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Admin
