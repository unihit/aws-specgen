/**
 * AWS Infrastructure Specification Viewer & Excel Generator.
 * 100% Client-side JSON parsing & Excel generation via ExcelJS.
 */

let specData = null;

// 스타일 상수 (고객사 보고서용 고품격 슬레이트 네이비 팔레트)
const STYLE = {
  navyHeader: { type: 'pattern', pattern: 'solid', fgColor: { argb: '1E3A8A' } },
  blueAltHeader: { type: 'pattern', pattern: 'solid', fgColor: { argb: '2563EB' } },
  zebraFill: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'F8FAFC' } },
  cardFill: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'F1F5F9' } },
  borderThin: {
    top: { style: 'thin', color: { argb: 'CBD5E1' } },
    left: { style: 'thin', color: { argb: 'CBD5E1' } },
    bottom: { style: 'thin', color: { argb: 'CBD5E1' } },
    right: { style: 'thin', color: { argb: 'CBD5E1' } }
  },
  stateRunning: {
    fill: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'DCFCE7' } },
    font: { name: '맑은 고딕', size: 10, bold: true, color: { argb: '15803D' } }
  },
  stateStopped: {
    fill: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FEE2E2' } },
    font: { name: '맑은 고딕', size: 10, bold: true, color: { argb: 'B91C1C' } }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');

  dropZone.addEventListener('click', () => fileInput.click());

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('border-blue-600', 'bg-blue-50/50');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('border-blue-600', 'bg-blue-50/50');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('border-blue-600', 'bg-blue-50/50');
    if (e.dataTransfer.files.length > 0) {
      loadFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      loadFile(e.target.files[0]);
    }
  });
});

function loadFile(file) {
  if (!file.name.endsWith('.json')) {
    alert('JSON 파일(.json)을 업로드해주세요.');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const json = JSON.parse(e.target.result);
      if (!json.meta || !json.resources) {
        alert('올바른 AWS SpecGen JSON 파일 형식이 아닙니다 (meta, resources 누락).');
        return;
      }
      specData = json;
      renderDashboard(json);
    } catch (err) {
      alert('JSON 파싱 실패: ' + err.message);
    }
  };
  reader.readAsText(file, 'utf-8');
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('border-blue-600', 'text-blue-600', 'font-bold');
    btn.classList.add('border-transparent', 'text-slate-600', 'font-medium');
  });

  document.getElementById(tabId).classList.add('active');
  const activeBtn = document.getElementById('btn-' + tabId);
  if (activeBtn) {
    activeBtn.classList.remove('border-transparent', 'text-slate-600', 'font-medium');
    activeBtn.classList.add('border-blue-600', 'text-blue-600', 'font-bold');
  }
}

function renderDashboard(data) {
  document.getElementById('drop-zone').classList.add('hidden');
  document.getElementById('dashboard-area').classList.remove('hidden');

  const meta = data.meta || {};
  const res = data.resources || {};

  document.getElementById('meta-region').innerText = meta.region || '-';
  document.getElementById('meta-account').innerText = meta.account_id || '-';
  document.getElementById('meta-scanned-at').innerText = (meta.scanned_at || '').slice(0, 19).replace('T', ' ');

  // Skipped 권한 경고
  const skippedContainer = document.getElementById('skipped-alert');
  if (meta.skipped && meta.skipped.length > 0) {
    skippedContainer.classList.remove('hidden');
    document.getElementById('skipped-list').innerText = meta.skipped.map(s => `${s.collector} (${s.reason})`).join(', ');
  } else {
    skippedContainer.classList.add('hidden');
  }

  // KPIs
  document.getElementById('kpi-vpc').innerText = (res.vpcs || []).length;
  document.getElementById('kpi-subnet').innerText = (res.subnets || []).length;
  document.getElementById('kpi-sg').innerText = (res.security_groups || []).length;
  document.getElementById('kpi-ec2').innerText = (res.ec2_instances || []).length;
  document.getElementById('kpi-rds').innerText = (res.rds_instances || []).length;
  document.getElementById('kpi-elb').innerText = (res.load_balancers || []).length;

  // Tables
  // VPC
  document.getElementById('table-vpc').innerHTML = (res.vpcs || []).map(v => `
    <tr class="hover:bg-slate-50">
      <td class="p-3 font-semibold text-slate-800">${v.name || '(No Name)'}</td>
      <td class="p-3 font-mono text-xs">${v.id}</td>
      <td class="p-3 font-mono">${v.cidr}</td>
      <td class="p-3">${v.is_default ? '예 (기본)' : '아니오 (사용자 생성)'}</td>
      <td class="p-3"><span class="px-2 py-0.5 rounded text-xs bg-emerald-100 text-emerald-800">${v.state}</span></td>
    </tr>
  `).join('') || '<tr><td colspan="5" class="p-4 text-center text-slate-400">자원 없음</td></tr>';

  // Subnets
  document.getElementById('table-subnet').innerHTML = (res.subnets || []).map(s => `
    <tr class="hover:bg-slate-50">
      <td class="p-3 font-semibold text-slate-800">${s.name || '(No Name)'}</td>
      <td class="p-3 font-mono text-xs">${s.id}</td>
      <td class="p-3 font-mono text-xs">${s.vpc_id}</td>
      <td class="p-3 font-mono">${s.cidr}</td>
      <td class="p-3">${s.az}</td>
      <td class="p-3"><span class="px-2 py-0.5 rounded text-xs ${s.type === 'Public' ? 'bg-blue-100 text-blue-800 font-bold' : 'bg-slate-100 text-slate-700'}">${s.type}</span></td>
      <td class="p-3 font-medium">${s.available_ips}</td>
    </tr>
  `).join('') || '<tr><td colspan="7" class="p-4 text-center text-slate-400">자원 없음</td></tr>';

  // Gateways
  const igws = res.internet_gateways || [];
  const nats = res.nat_gateways || [];
  const gwRows = [
    ...igws.map(i => `<tr><td class="p-3 font-bold text-blue-600">IGW</td><td class="p-3 font-semibold">${i.name || '-'}</td><td class="p-3 font-mono text-xs">${i.id}</td><td class="p-3 font-mono text-xs">${(i.attached_vpcs || []).join(', ')}</td><td class="p-3">-</td><td class="p-3">${i.state}</td></tr>`),
    ...nats.map(n => `<tr><td class="p-3 font-bold text-indigo-600">NAT GW</td><td class="p-3 font-semibold">${n.name || '-'}</td><td class="p-3 font-mono text-xs">${n.id}</td><td class="p-3 font-mono text-xs">${n.vpc_id}</td><td class="p-3 font-mono text-xs">${(n.public_ips || []).join(', ')}</td><td class="p-3">${n.state}</td></tr>`)
  ];
  document.getElementById('table-gateways').innerHTML = gwRows.join('') || '<tr><td colspan="6" class="p-4 text-center text-slate-400">게이트웨이 없음</td></tr>';

  // Route Tables
  document.getElementById('table-rtb').innerHTML = (res.route_tables || []).map(r => `
    <tr class="hover:bg-slate-50">
      <td class="p-3 font-semibold text-slate-800">${r.name || '-'}</td>
      <td class="p-3 font-mono text-xs">${r.id}</td>
      <td class="p-3 font-mono text-xs">${r.vpc_id}</td>
      <td class="p-3 text-xs">${(r.associated_subnets || []).join(', ') || (r.is_main ? '(Main RTB)' : '-')}</td>
      <td class="p-3 font-mono text-xs text-blue-600 font-semibold">${r.default_gateway}</td>
      <td class="p-3 text-xs text-slate-500">${r.routes_summary}</td>
    </tr>
  `).join('') || '<tr><td colspan="6" class="p-4 text-center text-slate-400">자원 없음</td></tr>';

  // Security Groups
  document.getElementById('table-sg').innerHTML = (res.security_groups || []).map(sg => `
    <tr class="hover:bg-slate-50">
      <td class="p-3 font-semibold text-slate-800">${sg.name}</td>
      <td class="p-3 font-mono text-xs">${sg.id}</td>
      <td class="p-3 font-mono text-xs">${sg.vpc_id}</td>
      <td class="p-3 text-xs font-mono whitespace-pre-line text-slate-700">${sg.inbound_rules_summary}</td>
      <td class="p-3 text-slate-500">${sg.description}</td>
    </tr>
  `).join('') || '<tr><td colspan="5" class="p-4 text-center text-slate-400">자원 없음</td></tr>';

  // EC2
  document.getElementById('table-ec2').innerHTML = (res.ec2_instances || []).map(i => `
    <tr class="hover:bg-slate-50">
      <td class="p-3 font-semibold text-slate-800">${i.name}</td>
      <td class="p-3 font-mono text-xs">${i.id}</td>
      <td class="p-3"><span class="px-2 py-0.5 rounded text-xs ${i.state === 'running' ? 'bg-emerald-100 text-emerald-800 font-bold' : 'bg-rose-100 text-rose-800'}">${i.state}</span></td>
      <td class="p-3 font-mono">${i.type}</td>
      <td class="p-3 font-mono">${i.private_ip}</td>
      <td class="p-3 font-mono">${i.public_ip}</td>
      <td class="p-3 font-mono text-xs">${i.subnet_id}</td>
      <td class="p-3">${i.az}</td>
      <td class="p-3">${i.ebs_total_gb} GB</td>
    </tr>
  `).join('') || '<tr><td colspan="9" class="p-4 text-center text-slate-400">자원 없음</td></tr>';

  // RDS
  document.getElementById('table-rds').innerHTML = (res.rds_instances || []).map(r => `
    <tr class="hover:bg-slate-50">
      <td class="p-3 font-semibold text-slate-800">${r.name}</td>
      <td class="p-3"><span class="px-2 py-0.5 rounded text-xs bg-emerald-100 text-emerald-800">${r.status}</span></td>
      <td class="p-3">${r.engine} ${r.version}</td>
      <td class="p-3 font-mono">${r.class}</td>
      <td class="p-3">${r.storage_gb} GB (${r.storage_type})</td>
      <td class="p-3">${r.multi_az ? '예 (Multi-AZ)' : '아니오 (Single-AZ)'}</td>
      <td class="p-3 font-mono text-xs">${r.endpoint}:${r.port}</td>
    </tr>
  `).join('') || '<tr><td colspan="7" class="p-4 text-center text-slate-400">자원 없음</td></tr>';

  // ELB
  document.getElementById('table-elb').innerHTML = (res.load_balancers || []).map(l => `
    <tr class="hover:bg-slate-50">
      <td class="p-3 font-semibold text-slate-800">${l.name}</td>
      <td class="p-3"><span class="px-2 py-0.5 rounded text-xs bg-indigo-100 text-indigo-800">${l.type}</span></td>
      <td class="p-3">${l.scheme}</td>
      <td class="p-3"><span class="px-2 py-0.5 rounded text-xs bg-emerald-100 text-emerald-800">${l.state}</span></td>
      <td class="p-3 font-mono text-xs truncate max-w-xs">${l.dns}</td>
      <td class="p-3 font-mono">${(l.listeners || []).join(', ')}</td>
    </tr>
  `).join('') || '<tr><td colspan="6" class="p-4 text-center text-slate-400">자원 없음</td></tr>';

  // S3
  document.getElementById('table-s3').innerHTML = (res.s3_buckets || []).map(b => `
    <tr class="hover:bg-slate-50">
      <td class="p-3 font-semibold text-slate-800">${b.name}</td>
      <td class="p-3">${b.region}</td>
      <td class="p-3">${b.encryption}</td>
      <td class="p-3">${b.versioning}</td>
      <td class="p-3">${b.created.slice(0, 16).replace('T', ' ')}</td>
    </tr>
  `).join('') || '<tr><td colspan="5" class="p-4 text-center text-slate-400">자원 없음</td></tr>';

  // Lambda
  document.getElementById('table-lambda').innerHTML = (res.lambda_functions || []).map(f => `
    <tr class="hover:bg-slate-50">
      <td class="p-3 font-semibold text-slate-800">${f.name}</td>
      <td class="p-3 font-mono text-xs">${f.runtime}</td>
      <td class="p-3">${f.memory_mb} MB</td>
      <td class="p-3">${f.timeout_s} 초</td>
      <td class="p-3 font-mono text-xs">${f.handler}</td>
      <td class="p-3">${f.last_modified.slice(0, 19).replace('T', ' ')}</td>
    </tr>
  `).join('') || '<tr><td colspan="6" class="p-4 text-center text-slate-400">자원 없음</td></tr>';
}

// 엑셀 생성 함수 (ExcelJS)
async function exportExcel() {
  if (!specData) {
    alert('스캔 데이터가 없습니다.');
    return;
  }

  const customer = document.getElementById('customer-input').value.trim() || '고객사';
  const meta = specData.meta || {};
  const res = specData.resources || {};
  const region = meta.region || 'ap-northeast-2';
  const scannedAt = (meta.scanned_at || '').slice(0, 19).replace('T', ' ');

  const workbook = new ExcelJS.Workbook();
  workbook.creator = 'AWS SpecGen';
  workbook.created = new Date();

  // 1. Overview Sheet
  const wsOverview = workbook.addWorksheet('00_인프라_요약_보고서', { views: [{ showGridLines: true }] });
  wsOverview.mergeCells('B2:F2');
  const titleCell = wsOverview.getCell('B2');
  titleCell.value = 'AWS 클라우드 인프라 생성 명세서';
  titleCell.font = { name: '맑은 고딕', size: 16, bold: true, color: { argb: '1E293B' } };
  titleCell.alignment = { vertical: 'middle' };
  wsOverview.getRow(2).height = 32;

  wsOverview.mergeCells('B3:F3');
  const subCell = wsOverview.getCell('B3');
  subCell.value = `본 문서는 ${customer} 제출용으로 자동 추출된 AWS 핵심 코어 및 네트워크 자원 구성 명세서입니다.`;
  subCell.font = { name: '맑은 고딕', size: 10, color: { argb: '64748B' } };

  // 메타 정보 표
  const metaRows = [
    ['고객사명', customer, '기준 리전 (Region)', region],
    ['AWS 계정 ID', meta.account_id || '-', '생성 일시', scannedAt]
  ];
  let curR = 5;
  metaRows.forEach(row => {
    const r = wsOverview.getRow(curR);
    r.getCell(2).value = row[0];
    r.getCell(2).font = { name: '맑은 고딕', bold: true };
    r.getCell(2).fill = STYLE.cardFill;
    r.getCell(2).border = STYLE.borderThin;
    r.getCell(2).alignment = { horizontal: 'center', vertical: 'middle' };

    r.getCell(3).value = row[1];
    r.getCell(3).font = { name: '맑은 고딕' };
    r.getCell(3).border = STYLE.borderThin;

    r.getCell(4).value = row[2];
    r.getCell(4).font = { name: '맑은 고딕', bold: true };
    r.getCell(4).fill = STYLE.cardFill;
    r.getCell(4).border = STYLE.borderThin;
    r.getCell(4).alignment = { horizontal: 'center', vertical: 'middle' };

    r.getCell(5).value = row[3];
    r.getCell(5).font = { name: '맑은 고딕' };
    r.getCell(5).border = STYLE.borderThin;
    r.height = 24;
    curR++;
  });

  // KPI 요약
  curR = 8;
  wsOverview.getCell(`B${curR}`).value = '■ 핵심 인프라 자원 수량 요약';
  wsOverview.getCell(`B${curR}`).font = { name: '맑은 고딕', size: 12, bold: true, color: { argb: '0F172A' } };
  curR++;

  const kpiHeaders = ['No', '서비스 영역', '자원 구분 (Resource)', '인프라 수량', '핵심 설명'];
  const hRow = wsOverview.getRow(curR);
  kpiHeaders.forEach((h, idx) => {
    const c = hRow.getCell(idx + 2);
    c.value = h;
    c.font = { name: '맑은 고딕', size: 10, bold: true, color: { argb: 'FFFFFF' } };
    c.fill = STYLE.navyHeader;
    c.alignment = { horizontal: 'center', vertical: 'middle' };
    c.border = STYLE.borderThin;
  });
  hRow.height = 26;
  curR++;

  const kpis = [
    [1, '네트워크 (Network)', 'VPC (가상 사설 네트워크)', `${(res.vpcs || []).length} 개`, '격리된 가상 클라우드 네트워크'],
    [2, '네트워크 (Network)', '서브넷 (Subnets)', `${(res.subnets || []).length} 개`, 'Public / Private 망 분리 서브넷'],
    [3, '네트워크 (Network)', '인터넷 / NAT 게이트웨이', `${(res.internet_gateways || []).length} / ${(res.nat_gateways || []).length} 개`, '외부 통신 및 아웃바운드 게이트웨이'],
    [4, '보안 (Security)', '보안 그룹 (Security Groups)', `${(res.security_groups || []).length} 개`, '가상 방화벽 인바운드/아웃바운드 규칙'],
    [5, '컴퓨팅 (Compute)', 'EC2 가상 서버 인스턴스', `${(res.ec2_instances || []).length} 대`, '애플리케이션 및 WAS 서버'],
    [6, '데이터베이스 (DB)', 'RDS / Aurora 인스턴스', `${(res.rds_instances || []).length} 개`, '관리형 관계형 데이터베이스 인스턴스'],
    [7, '로드밸런서 (ELB)', 'Application / Network LB', `${(res.load_balancers || []).length} 대`, '트래픽 부하분산 및 리스너 포트'],
    [8, '스토리지 (Storage)', 'S3 버킷', `${(res.s3_buckets || []).length} 개`, '정적 웹 및 백업 오브젝트 저장소'],
    [9, '서버리스 (Serverless)', 'Lambda 함수', `${(res.lambda_functions || []).length} 개`, '이벤트 기반 서버리스 컴퓨팅 함수']
  ];

  kpis.forEach((row, i) => {
    const r = wsOverview.getRow(curR);
    row.forEach((val, cIdx) => {
      const c = r.getCell(cIdx + 2);
      c.value = val;
      c.font = { name: '맑은 고딕', size: 10 };
      c.border = STYLE.borderThin;
      if (i % 2 === 1) c.fill = STYLE.zebraFill;
      c.alignment = (cIdx === 0 || cIdx === 3) ? { horizontal: 'center', vertical: 'middle' } : { horizontal: 'left', vertical: 'middle' };
    });
    r.height = 22;
    curR++;
  });

  wsOverview.getColumn(1).width = 4;
  wsOverview.getColumn(2).width = 8;
  wsOverview.getColumn(3).width = 24;
  wsOverview.getColumn(4).width = 28;
  wsOverview.getColumn(5).width = 16;
  wsOverview.getColumn(6).width = 40;

  // 헬퍼: 테이블 시트 생성
  function addTableSheet(sheetName, title, headers, rows, headerFill = STYLE.navyHeader) {
    const ws = workbook.addWorksheet(sheetName, { views: [{ showGridLines: true }] });
    ws.getCell('A1').value = title;
    ws.getCell('A1').font = { name: '맑은 고딕', size: 12, bold: true, color: { argb: '0F172A' } };

    const hr = ws.getRow(2);
    headers.forEach((h, idx) => {
      const c = hr.getCell(idx + 1);
      c.value = h;
      c.font = { name: '맑은 고딕', size: 10, bold: true, color: { argb: 'FFFFFF' } };
      c.fill = headerFill;
      c.alignment = { horizontal: 'center', vertical: 'middle' };
      c.border = STYLE.borderThin;
    });
    hr.height = 26;

    let rNum = 3;
    rows.forEach((rVals, idx) => {
      const r = ws.getRow(rNum);
      rVals.forEach((val, cIdx) => {
        const c = r.getCell(cIdx + 1);
        c.value = val;
        c.font = { name: '맑은 고딕', size: 10 };
        c.border = STYLE.borderThin;
        if (idx % 2 === 1) c.fill = STYLE.zebraFill;
        c.alignment = { vertical: 'middle' };
      });
      r.height = 22;
      rNum++;
    });

    // Auto Column Width
    headers.forEach((h, idx) => {
      let maxLen = h.length * 2.2;
      rows.forEach(r => {
        const str = String(r[idx] || '');
        const l = str.length * (str.charCodeAt(0) > 127 ? 1.8 : 1.1);
        if (l > maxLen) maxLen = l;
      });
      ws.getColumn(idx + 1).width = Math.max(14, Math.min(Math.ceil(maxLen) + 4, 60));
    });
  }

  // 2. VPC
  const vpcRows = (res.vpcs || []).map(v => [v.name || '-', v.id, v.cidr, v.is_default ? '예 (기본)' : '아니오 (사용자 생성)', v.state, v.dhcp]);
  addTableSheet('01_네트워크_VPC', '■ VPC (Virtual Private Cloud) 명세', ['VPC 이름', 'VPC ID', 'IPv4 CIDR', '기본 여부', '상태', 'DHCP ID'], vpcRows);

  // 3. Subnets
  const subRows = (res.subnets || []).map(s => [s.name || '-', s.id, s.vpc_id, s.cidr, s.az, s.type, s.available_ips, s.state]);
  addTableSheet('02_서브넷_Subnet', '■ 서브넷 (Subnet) 상세 명세', ['서브넷 이름', '서브넷 ID', '소속 VPC ID', 'IPv4 CIDR', '가용영역', '망 구분', '가용 IP', '상태'], subRows, STYLE.blueAltHeader);

  // 4. Gateways & Routing
  const gwRows = [
    ...(res.internet_gateways || []).map(i => ['인터넷 GW (IGW)', i.name || '-', i.id, (i.attached_vpcs || []).join(', '), '-', i.state]),
    ...(res.nat_gateways || []).map(n => ['NAT Gateway', n.name || '-', n.id, n.vpc_id, (n.public_ips || []).join(', '), n.state])
  ];
  addTableSheet('03_게이트웨이', '■ 인터넷 및 NAT 게이트웨이 명세', ['구분', '이름', '게이트웨이 ID', '소속 VPC', '탄력적 IP (EIP)', '상태'], gwRows);

  // 5. Route Tables
  const rtbRows = (res.route_tables || []).map(r => [r.name || '-', r.id, r.vpc_id, (r.associated_subnets || []).join(', ') || (r.is_main ? '(Main RTB)' : '-'), r.default_gateway, r.routes_summary]);
  addTableSheet('04_라우팅테이블', '■ 라우팅 테이블 (Route Table) 명세', ['이름', 'Route Table ID', '소속 VPC ID', '연결 서브넷', '기본 게이트웨이 (0.0.0.0/0)', '주요 라우팅 요약'], rtbRows);

  // 6. Security Groups
  const sgRows = (res.security_groups || []).map(sg => [sg.name, sg.id, sg.group_name, sg.vpc_id, sg.inbound_rules_summary, sg.description]);
  addTableSheet('05_보안그룹', '■ 보안 그룹 (Security Group) 인바운드 방화벽 명세', ['보안그룹 명칭', 'Group ID', '코드명', '소속 VPC', '인바운드 허용 룰 요약', '설명'], sgRows);

  // 7. EC2
  const ec2Rows = (res.ec2_instances || []).map(i => [i.name, i.id, i.state, i.type, i.private_ip, i.public_ip, i.subnet_id, i.az, `${i.ebs_total_gb} GB`, i.platform, i.key_name, i.launch_time]);
  addTableSheet('06_컴퓨팅_EC2', '■ EC2 가상 서버 인스턴스 명세', ['인스턴스 이름', 'Instance ID', '상태', '인스턴스 타입', 'Private IP', 'Public IP', '서브넷 ID', '가용영역', 'EBS 총용량', '플랫폼', '키페어', '생성/시작일시'], ec2Rows);

  // 8. RDS
  const rdsRows = (res.rds_instances || []).map(r => [r.name, r.status, `${r.engine} ${r.version}`, r.class, `${r.storage_gb} GB (${r.storage_type})`, r.multi_az ? '예' : '아니오', `${r.endpoint}:${r.port}`, r.vpc_id, r.publicly_accessible ? '공개' : '비공개']);
  addTableSheet('07_데이터베이스_RDS', '■ 관계형 데이터베이스 (RDS / Aurora) 명세', ['DB 식별자', '상태', '엔진 및 버전', '인스턴스 클래스', '스토리지', 'Multi-AZ', '접속 엔드포인트', 'VPC ID', '퍼블릭 접근'], rdsRows);

  // 9. ELB
  const elbRows = (res.load_balancers || []).map(l => [l.name, l.type, l.scheme, l.state, l.dns, l.vpc_id, (l.listeners || []).join(', '), (l.target_groups || []).join(', ')]);
  addTableSheet('08_로드밸런서_ELB', '■ Load Balancer (ALB / NLB) 명세', ['LB 이름', '유형', '스킴', '상태', 'DNS 엔드포인트', '소속 VPC ID', '리스너 포트', '대상 그룹'], elbRows);

  // 10. S3 & Lambda
  const s3Rows = (res.s3_buckets || []).map(b => [b.name, b.region, b.encryption, b.versioning, b.public_access_blocked ? '차단됨 (안전)' : '미차단', b.created]);
  addTableSheet('09_스토리지_S3', '■ Simple Storage Service (S3) 버킷 명세', ['버킷 이름', '배치 리전', '기본 암호화', '버전 관리', '퍼블릭 액세스 차단', '생성 일시'], s3Rows);

  const lmbRows = (res.lambda_functions || []).map(f => [f.name, f.runtime, `${f.memory_mb} MB`, `${f.timeout_s} 초`, f.handler, f.role, f.vpc_id, f.last_modified]);
  addTableSheet('10_서버리스_Lambda', '■ AWS Lambda 함수 명세', ['함수 이름', '런타임', '할당 메모리', '타임아웃', '핸들러', '실행 역할(IAM)', 'VPC 연결', '최근 수정일시'], lmbRows);

  // 엑셀 파일 저장 및 브라우저 다운로드
  const buffer = await workbook.xlsx.writeBuffer();
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  const outFilename = `AWS_인프라_생성명세서_${customer}_${region}_${dateStr}.xlsx`;

  // 다운로드 링크 트리거
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = outFilename;
  link.click();
  URL.revokeObjectURL(link.href);
}
