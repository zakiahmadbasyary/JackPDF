import sys, os
sys.path.insert(0, os.getcwd())
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame,
    QProgressBar, QCheckBox
)
from PySide6.QtCore import Qt
from app.utils.icon_utils import get_feature_icon
from app.ui.pages.merge_page import PdfPreviewPanel
from app.ui.pages.split_page import RangeRowWidget

app = QApplication(sys.argv)
with open('assets/styles/light.qss', 'r') as f:
    app.setStyleSheet(f.read())

w = QWidget()
w.setStyleSheet('background: #F7F9FC;')
root = QVBoxLayout(w)
root.setContentsMargins(32, 28, 32, 28)
root.setSpacing(16)

# Header
header = QHBoxLayout()
header.setSpacing(12)
header.setAlignment(Qt.AlignmentFlag.AlignVCenter)
back_btn = QPushButton('←  Kembali')
back_btn.setObjectName('SecondaryButton')
icon = QLabel()
pix = get_feature_icon('Split PDF', size=40)
icon.setPixmap(pix)
icon.setFixedSize(40, 40)
tb = QVBoxLayout()
tb.setSpacing(2)
tb.setContentsMargins(0, 0, 0, 0)
t = QLabel('Split PDF')
t.setObjectName('PageTitle')
s = QLabel('Pisahkan halaman dokumen PDF sesuai rentang kebutuhan Anda.')
s.setObjectName('PageSubtitle')
tb.addWidget(t)
tb.addWidget(s)
header.addWidget(back_btn)
header.addWidget(icon)
header.addLayout(tb)
header.addStretch()
root.addLayout(header)

# Info Card
info_card = QFrame()
info_card.setObjectName('InfoCard')
il = QHBoxLayout(info_card)
il.setContentsMargins(16, 12, 16, 12)
info_icon = QLabel()
info_icon.setPixmap(pix)
info_icon.setFixedSize(36, 36)
il.addWidget(info_icon)
details_lbl = QLabel('sample_split.pdf\n10 Halaman • 24.5 KB')
details_lbl.setObjectName('FileDetailsText')
il.addWidget(details_lbl, stretch=1)
change_btn = QPushButton('Ganti File')
change_btn.setObjectName('SecondaryButton')
il.addWidget(change_btn)
toggle_prev = QPushButton('Sembunyikan Pratinjau')
toggle_prev.setObjectName('SecondaryButton')
il.addWidget(toggle_prev)
root.addWidget(info_card)

# Main Two-Column Layout
main_layout = QHBoxLayout()
main_layout.setSpacing(16)

# Left: Range card & actions
left_col = QWidget()
ll = QVBoxLayout(left_col)
ll.setContentsMargins(0, 0, 0, 0)
ll.setSpacing(14)

rc = QFrame()
rc.setObjectName('FeatureCard')
rcl = QVBoxLayout(rc)
rcl.setContentsMargins(20, 18, 20, 18)
rcl.setSpacing(12)
rt = QLabel('Pengaturan Rentang Halaman')
rt.setObjectName('SectionTitle')
rcl.addWidget(rt)

row1 = RangeRowWidget(1, 1, 5, 10)
row2 = RangeRowWidget(2, 6, 10, 10)
rcl.addWidget(row1)
rcl.addWidget(row2)

add_btn = QPushButton('+ Tambah Rentang')
add_btn.setObjectName('SecondaryButton')
rcl.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignLeft)

chk = QCheckBox('Gabungkan semua rentang menjadi 1 file PDF (Merge Split)')
chk.setObjectName('StyledCheckBox')
chk.setChecked(True)
rcl.addWidget(chk)

ll.addWidget(rc)

# Bottom bar
bb = QHBoxLayout()
sp_btn = QPushButton('Split PDF Sekarang')
sp_btn.setObjectName('ActionLargeButton')
rst_btn = QPushButton('Reset Form')
rst_btn.setObjectName('SecondaryButton')
bb.addWidget(sp_btn)
bb.addWidget(rst_btn)
bb.addStretch()
ll.addLayout(bb)
ll.addStretch()

# Right: Preview panel
prev = PdfPreviewPanel()
prev.load_document('scratch/sample_split.pdf', 0)

main_layout.addWidget(left_col, stretch=1)
main_layout.addWidget(prev, stretch=0)
root.addLayout(main_layout)

w.resize(1060, 720)
w.show()
app.processEvents()
w.grab().save('scratch/split_with_preview_mockup.png')
print('Mockup saved to scratch/split_with_preview_mockup.png')
