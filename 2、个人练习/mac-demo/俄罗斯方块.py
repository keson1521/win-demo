"""
俄罗斯方块
操作说明：
  ←  →     左右移动
  ↓         加速下落
  ↑         旋转
  Space     硬降（直接落底）
  P         暂停 / 继续
  R         重新开始
"""

import pygame
import random
import sys

# ── 常量 ─────────────────────────────────────────
COLS, ROWS = 10, 20
CELL = 32                          # 每格像素
BOARD_W = COLS * CELL              # 320
BOARD_H = ROWS * CELL              # 640
PANEL_W = 200                      # 右侧信息面板
WIN_W   = BOARD_W + PANEL_W        # 520
WIN_H   = BOARD_H                  # 640
FPS     = 60

# 颜色
BLACK   = (  0,   0,   0)
WHITE   = (255, 255, 255)
GRAY    = ( 40,  40,  40)
LGRAY   = (100, 100, 100)
BG      = ( 18,  18,  18)
PANEL   = ( 28,  28,  28)

# 七种方块颜色（对应 I O T S Z J L）
COLORS = [
    None,                        # 0 = 空
    (  0, 240, 240),             # 1 I 青
    (240, 240,   0),             # 2 O 黄
    (160,   0, 240),             # 3 T 紫
    (  0, 240,   0),             # 4 S 绿
    (240,   0,   0),             # 5 Z 红
    (  0,   0, 240),             # 6 J 蓝
    (240, 160,   0),             # 7 L 橙
]

# 七种方块的旋转状态（行列偏移列表）
SHAPES = {
    'I': [[(0,1),(1,1),(2,1),(3,1)],
          [(1,0),(1,1),(1,2),(1,3)],
          [(0,2),(1,2),(2,2),(3,2)],
          [(2,0),(2,1),(2,2),(2,3)]],

    'O': [[(0,0),(0,1),(1,0),(1,1)]]*4,

    'T': [[(0,1),(1,0),(1,1),(1,2)],
          [(0,1),(1,1),(1,2),(2,1)],
          [(1,0),(1,1),(1,2),(2,1)],
          [(0,1),(1,0),(1,1),(2,1)]],

    'S': [[(0,1),(0,2),(1,0),(1,1)],
          [(0,1),(1,1),(1,2),(2,2)],
          [(1,1),(1,2),(2,0),(2,1)],
          [(0,0),(1,0),(1,1),(2,1)]],

    'Z': [[(0,0),(0,1),(1,1),(1,2)],
          [(0,2),(1,1),(1,2),(2,1)],
          [(1,0),(1,1),(2,1),(2,2)],
          [(0,1),(1,0),(1,1),(2,0)]],

    'J': [[(0,0),(1,0),(1,1),(1,2)],
          [(0,1),(0,2),(1,1),(2,1)],
          [(1,0),(1,1),(1,2),(2,2)],
          [(0,1),(1,1),(2,0),(2,1)]],

    'L': [[(0,2),(1,0),(1,1),(1,2)],
          [(0,1),(1,1),(1,2),(2,2)],  # fixed
          [(1,0),(1,1),(1,2),(2,0)],
          [(0,0),(0,1),(1,1),(2,1)]],
}

SHAPE_NAMES = list(SHAPES.keys())
SHAPE_ID    = {name: i+1 for i, name in enumerate(SHAPE_NAMES)}  # I=1 … L=7

# 得分表
SCORE_TABLE = {1: 100, 2: 300, 3: 500, 4: 800}


# ── 工具函数 ──────────────────────────────────────
def draw_cell(surf, r, c, color, origin_x=0, origin_y=0, alpha=255):
    x = origin_x + c * CELL
    y = origin_y + r * CELL
    rect = pygame.Rect(x+1, y+1, CELL-2, CELL-2)
    if alpha < 255:
        s = pygame.Surface((CELL-2, CELL-2), pygame.SRCALPHA)
        s.fill((*color, alpha))
        surf.blit(s, (x+1, y+1))
    else:
        pygame.draw.rect(surf, color, rect, border_radius=3)
        # 高光
        pygame.draw.line(surf, tuple(min(v+60,255) for v in color),
                         (x+2, y+2), (x+CELL-3, y+2), 2)


# ── 方块类 ────────────────────────────────────────
class Piece:
    def __init__(self, name=None):
        self.name  = name or random.choice(SHAPE_NAMES)
        self.rot   = 0
        self.color = COLORS[SHAPE_ID[self.name]]
        self.row   = 0
        self.col   = COLS // 2 - 2

    def cells(self, row=None, col=None, rot=None):
        r = self.row if row is None else row
        c = self.col if col is None else col
        s = self.rot if rot  is None else rot
        return [(r + dr, c + dc) for dr, dc in SHAPES[self.name][s % 4]]


# ── 游戏逻辑 ──────────────────────────────────────
class Tetris:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board     = [[0]*COLS for _ in range(ROWS)]
        self.score     = 0
        self.lines     = 0
        self.level     = 1
        self.game_over = False
        self.paused    = False
        self.bag       = []
        self.current   = self._next_piece()
        self.next      = self._next_piece()
        self._reset_timer()

    # ── 随机包（7-bag） ────────────────────────────
    def _next_piece(self):
        if not self.bag:
            self.bag = SHAPE_NAMES[:]
            random.shuffle(self.bag)
        return Piece(self.bag.pop())

    def _reset_timer(self):
        self.drop_interval = max(100, 800 - (self.level-1)*75)  # ms
        self.drop_timer    = 0

    # ── 碰撞检测 ───────────────────────────────────
    def _valid(self, piece, row=None, col=None, rot=None):
        for r, c in piece.cells(row, col, rot):
            if r < 0 or r >= ROWS or c < 0 or c >= COLS:
                return False
            if r >= 0 and self.board[r][c]:
                return False
        return True

    # ── 操作 ───────────────────────────────────────
    def move(self, dr, dc):
        nr, nc = self.current.row + dr, self.current.col + dc
        if self._valid(self.current, row=nr, col=nc):
            self.current.row, self.current.col = nr, nc
            return True
        return False

    def rotate(self):
        new_rot = (self.current.rot + 1) % 4
        # Wall kick: 尝试原位、左移1、右移1、左移2、右移2
        for dc in (0, -1, 1, -2, 2):
            if self._valid(self.current, col=self.current.col+dc, rot=new_rot):
                self.current.col += dc
                self.current.rot  = new_rot
                return

    def hard_drop(self):
        while self.move(1, 0):
            self.score += 2
        self._lock()

    def _lock(self):
        for r, c in self.current.cells():
            if r < 0:
                self.game_over = True
                return
            self.board[r][c] = SHAPE_ID[self.current.name]
        cleared = self._clear_lines()
        if cleared:
            self.score += SCORE_TABLE.get(cleared, 0) * self.level
            self.lines += cleared
            self.level  = self.lines // 10 + 1
            self._reset_timer()
        self.current = self.next
        self.next    = self._next_piece()
        if not self._valid(self.current):
            self.game_over = True

    def _clear_lines(self):
        full = [r for r in range(ROWS) if all(self.board[r])]
        for r in full:
            del self.board[r]
            self.board.insert(0, [0]*COLS)
        return len(full)

    # ── 幽灵块（落点预览）─────────────────────────
    def ghost_row(self):
        r = self.current.row
        while self._valid(self.current, row=r+1):
            r += 1
        return r

    # ── 更新（每帧调用）───────────────────────────
    def update(self, dt):
        if self.paused or self.game_over:
            return
        self.drop_timer += dt
        if self.drop_timer >= self.drop_interval:
            self.drop_timer = 0
            if not self.move(1, 0):
                self._lock()


# ── 渲染 ──────────────────────────────────────────
class Renderer:
    def __init__(self, surf):
        self.surf  = surf
        self.font  = pygame.font.SysFont("微软雅黑", 18, bold=True)
        self.font_s = pygame.font.SysFont("微软雅黑", 14)
        self.font_big = pygame.font.SysFont("微软雅黑", 36, bold=True)

    def draw(self, game):
        self.surf.fill(BG)
        self._draw_board(game)
        self._draw_panel(game)
        if game.paused and not game.game_over:
            self._overlay("⏸  暂停中  P 继续")
        if game.game_over:
            self._overlay("游戏结束  R 重新开始")

    # ── 棋盘区 ────────────────────────────────────
    def _draw_board(self, game):
        # 网格底色
        for r in range(ROWS):
            for c in range(COLS):
                pygame.draw.rect(self.surf, GRAY,
                                 (c*CELL+1, r*CELL+1, CELL-2, CELL-2),
                                 border_radius=2)

        # 已堆叠方块
        for r in range(ROWS):
            for c in range(COLS):
                cid = game.board[r][c]
                if cid:
                    draw_cell(self.surf, r, c, COLORS[cid])

        # 幽灵块
        if not game.game_over:
            ghost_r = game.ghost_row()
            for dr, dc in SHAPES[game.current.name][game.current.rot]:
                r = ghost_r + dr
                c = game.current.col + dc
                if 0 <= r < ROWS and 0 <= c < COLS:
                    draw_cell(self.surf, r, c, game.current.color, alpha=60)

        # 当前方块
        if not game.game_over:
            for r, c in game.current.cells():
                if 0 <= r < ROWS:
                    draw_cell(self.surf, r, c, game.current.color)

        # 边框
        pygame.draw.rect(self.surf, LGRAY, (0, 0, BOARD_W, BOARD_H), 2)

    # ── 信息面板 ──────────────────────────────────
    def _draw_panel(self, game):
        px = BOARD_W + 10
        panel_rect = pygame.Rect(BOARD_W, 0, PANEL_W, WIN_H)
        pygame.draw.rect(self.surf, PANEL, panel_rect)

        # NEXT 预览
        self._label("下一个", px, 20)
        self._draw_mini(game.next, px + 20, 50)

        # 分割线
        pygame.draw.line(self.surf, LGRAY, (BOARD_W+10, 155), (WIN_W-10, 155), 1)

        # 分数
        self._label("得  分", px, 175)
        self._value(str(game.score), px, 200)

        # 行数
        self._label("消行数", px, 240)
        self._value(str(game.lines), px, 265)

        # 等级
        self._label("等  级", px, 305)
        self._value(str(game.level), px, 330)

        # 操作提示
        pygame.draw.line(self.surf, LGRAY, (BOARD_W+10, 390), (WIN_W-10, 390), 1)
        tips = ["← → 移动", "↑  旋转", "↓  加速", "Space 落底",
                "P  暂停", "R  重置"]
        for i, t in enumerate(tips):
            txt = self.font_s.render(t, True, LGRAY)
            self.surf.blit(txt, (px, 400 + i*26))

    def _label(self, text, x, y):
        s = self.font_s.render(text, True, LGRAY)
        self.surf.blit(s, (x, y))

    def _value(self, text, x, y):
        s = self.font.render(text, True, WHITE)
        self.surf.blit(s, (x, y))

    def _draw_mini(self, piece, ox, oy):
        """在右侧面板中绘制小预览"""
        cells = SHAPES[piece.name][0]
        # 居中
        min_c = min(c for _, c in cells)
        min_r = min(r for r, _ in cells)
        s = 24
        for r, c in cells:
            x = ox + (c - min_c) * s
            y = oy + (r - min_r) * s
            rect = pygame.Rect(x+1, y+1, s-2, s-2)
            pygame.draw.rect(self.surf, piece.color, rect, border_radius=3)
            pygame.draw.line(self.surf, tuple(min(v+60,255) for v in piece.color),
                             (x+2, y+2), (x+s-3, y+2), 2)

    def _overlay(self, text):
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.surf.blit(overlay, (0, 0))
        txt = self.font_big.render(text, True, WHITE)
        r = txt.get_rect(center=(WIN_W//2, WIN_H//2))
        self.surf.blit(txt, r)


# ── 主循环 ────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("俄罗斯方块")
    clock    = pygame.time.Clock()
    game     = Tetris()
    renderer = Renderer(screen)

    # 左右连续移动的按键重复参数
    pygame.key.set_repeat(170, 55)

    while True:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game.reset()
                elif event.key == pygame.K_p and not game.game_over:
                    game.paused = not game.paused
                elif not game.paused and not game.game_over:
                    if   event.key == pygame.K_LEFT:  game.move(0, -1)
                    elif event.key == pygame.K_RIGHT: game.move(0,  1)
                    elif event.key == pygame.K_DOWN:  game.move(1,  0)
                    elif event.key == pygame.K_UP:    game.rotate()
                    elif event.key == pygame.K_SPACE: game.hard_drop()

        game.update(dt)
        renderer.draw(game)
        pygame.display.flip()


if __name__ == "__main__":
    main()
