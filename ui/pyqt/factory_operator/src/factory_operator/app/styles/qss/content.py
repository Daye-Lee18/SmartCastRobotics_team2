"""콘텐츠 영역 위젯 — 카드 / 입력 / 버튼 / 테이블 / 리스트."""

from __future__ import annotations

from app.styles.tokens import Tokens


def _cards(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    sp = t.spacing
    r = t.radius
    return f"""
#kpiCard, #chartCard, #tableCard, #gaugeCard, #controlPanel,
#amrCard, #conveyorCard, #defectPanel, #cardSection, .Card {{
    background-color: {c.bg_card};
    border: 1px solid {c.border};
    border-radius: {r.xl}px;
}}
QGroupBox {{
    background-color: {c.bg_card};
    color: {c.text_primary};
    border: 1px solid {c.border};
    border-radius: {r.lg}px;
    margin-top: {sp.md}px;
    padding-top: {sp.lg}px;
    font-size: {typo.size_md}px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: {sp.md}px;
    padding: 0 {sp.sm}px;
    color: {c.text_primary};
    background-color: {c.bg_card};
}}
#kpiTitle {{
    color: {c.text_muted};
    font-size: {typo.size_sm}px;
    font-weight: 500;
    background-color: transparent;
}}
#kpiValue {{
    color: {c.text_primary};
    font-size: {typo.size_3xl}px;
    font-weight: 700;
    background-color: transparent;
}}
#kpiUnit {{
    color: {c.text_muted};
    font-size: {typo.size_sm}px;
    padding-bottom: {sp.xs}px;
    background-color: transparent;
}}
#kpiDelta[trend="up"]   {{ color: {c.ok};      font-weight: 600; }}
#kpiDelta[trend="down"] {{ color: {c.danger};  font-weight: 600; }}
#kpiDelta[trend="flat"] {{ color: {c.text_muted}; }}
"""


def _inputs(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    sp = t.spacing
    r = t.radius
    return f"""
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit,
QDateEdit, QTimeEdit, QDateTimeEdit {{
    background-color: {c.bg_card};
    color: {c.text_primary};
    border: 1px solid {c.border_strong};
    border-radius: {r.md}px;
    padding: {sp.xs + 2}px {sp.sm}px;
    font-size: {typo.size_md}px;
    selection-background-color: {c.selection_bg};
    selection-color: {c.selection_text};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QTextEdit:focus, QPlainTextEdit:focus, QDateEdit:focus {{
    border: 2px solid {c.brand};
    padding: {sp.xs + 1}px {sp.sm - 1}px;
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QTextEdit:disabled {{
    background-color: {c.bg_muted};
    color: {c.text_muted};
    border-color: {c.border};
}}
QLineEdit[error="true"], QComboBox[error="true"], QSpinBox[error="true"] {{
    border-color: {c.danger};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background-color: {c.bg_card};
    color: {c.text_primary};
    border: 1px solid {c.border};
    border-radius: {r.md}px;
    selection-background-color: {c.brand_subtle};
    selection-color: {c.text_primary};
    padding: {sp.xs}px;
    outline: 0;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background-color: {c.bg_muted};
    border: none;
    width: 18px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {c.border_strong};
}}
QCheckBox, QRadioButton {{
    color: {c.text_primary};
    background-color: transparent;
    spacing: {sp.sm}px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {c.border_strong};
    border-radius: {r.sm}px;
    background-color: {c.bg_card};
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {c.brand};
    border-color: {c.brand};
}}
"""


def _buttons(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    sp = t.spacing
    r = t.radius
    return f"""
QPushButton {{
    background-color: {c.brand};
    color: {c.brand_text_on};
    border: 1px solid transparent;
    border-radius: {r.md}px;
    padding: {sp.sm - 1}px {sp.md + 2}px;
    font-size: {typo.size_md}px;
    font-weight: 600;
    min-height: 18px;
}}
QPushButton:hover  {{ background-color: {c.brand_hover}; }}
QPushButton:pressed {{ background-color: {c.brand_hover}; padding-top: {sp.sm}px; padding-bottom: {sp.sm - 2}px; }}
QPushButton:disabled {{ background-color: {c.border_strong}; color: {c.text_muted}; }}

QPushButton[variant="secondary"] {{
    background-color: {c.bg_muted};
    color: {c.text_primary};
    border: 1px solid {c.border_strong};
}}
QPushButton[variant="secondary"]:hover {{ background-color: {c.border}; }}

QPushButton[variant="outline"] {{
    background-color: transparent;
    color: {c.brand};
    border: 1px solid {c.brand};
}}
QPushButton[variant="outline"]:hover {{ background-color: {c.brand_subtle}; }}

QPushButton[variant="ghost"] {{
    background-color: transparent;
    color: {c.text_secondary};
    border: 1px solid transparent;
}}
QPushButton[variant="ghost"]:hover {{ background-color: {c.bg_muted}; color: {c.text_primary}; }}

QPushButton[variant="danger"]  {{ background-color: {c.danger}; color: {c.brand_text_on}; }}
QPushButton[variant="success"] {{ background-color: {c.ok};     color: {c.brand_text_on}; }}
QPushButton[variant="warn"]    {{ background-color: {c.warn};   color: {c.brand_text_on}; }}

QPushButton[size="sm"] {{ padding: {sp.xs + 1}px {sp.sm + 2}px; font-size: {typo.size_sm}px; }}
QPushButton[size="lg"] {{ padding: {sp.md - 2}px {sp.lg + 4}px; font-size: {typo.size_lg}px; }}

QToolButton {{
    background-color: transparent;
    color: {c.text_secondary};
    border: 1px solid transparent;
    border-radius: {r.sm}px;
    padding: {sp.xs}px {sp.sm}px;
}}
QToolButton:hover {{
    background-color: {c.bg_muted};
    color: {c.text_primary};
}}
"""


def _tables(t: Tokens) -> str:
    c = t.color
    typo = t.typography
    sp = t.spacing
    r = t.radius
    return f"""
QTableWidget, QTableView {{
    background-color: {c.bg_card};
    color: {c.text_primary};
    border: 1px solid {c.border};
    border-radius: {r.lg}px;
    gridline-color: {c.border};
    font-size: {typo.size_base}px;
    selection-background-color: {c.selection_bg};
    selection-color: {c.selection_text};
    alternate-background-color: {c.bg_elevated};
    outline: 0;
}}
QTableWidget::item, QTableView::item {{
    padding: {sp.xs + 2}px {sp.sm + 2}px;
    border: none;
    border-bottom: 1px solid {c.border};
    color: {c.text_primary};
}}
QTableWidget::item:hover, QTableView::item:hover {{ background-color: {c.bg_elevated}; }}
QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {c.selection_bg}; color: {c.selection_text};
}}
QHeaderView::section {{
    background-color: {c.bg_muted};
    color: {c.text_secondary};
    padding: {sp.sm}px {sp.sm + 2}px;
    border: none;
    border-right: 1px solid {c.border};
    border-bottom: 2px solid {c.border};
    font-weight: 600;
    font-size: {typo.size_sm}px;
}}
QHeaderView::section:hover {{ background-color: {c.border}; }}

QListWidget {{
    background-color: {c.bg_card};
    border: 1px solid {c.border};
    border-radius: {r.lg}px;
    color: {c.text_primary};
    padding: {sp.xs}px;
    outline: 0;
}}
QListWidget::item {{
    padding: {sp.sm}px {sp.md}px;
    border-radius: {r.sm}px;
    color: {c.text_primary};
}}
QListWidget::item:hover {{ background-color: {c.bg_elevated}; }}
QListWidget::item:selected {{ background-color: {c.brand_subtle}; color: {c.text_primary}; }}
"""
