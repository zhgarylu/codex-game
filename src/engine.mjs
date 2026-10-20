export const CHEFS = [
  { id: 'blue', name: 'BLUE', title: '蓝色厨师', perk: '清爽蓝', color: '#6996d3', min: 1.2, max: 3.1, patience: 24, bonus: 1 },
  { id: 'green', name: 'GREEN', title: '绿色厨师', perk: '薄荷绿', color: '#70a783', min: 1.2, max: 3.1, patience: 24, bonus: 1 },
  { id: 'yellow', name: 'YELLOW', title: '黄色厨师', perk: '暖阳黄', color: '#e2b759', min: 1.2, max: 3.1, patience: 24, bonus: 1 },
  { id: 'red', name: 'RED', title: '红色厨师', perk: '番茄红', color: '#d47c7c', min: 1.2, max: 3.1, patience: 24, bonus: 1 },
];
export const BROTHS = ['豚骨白汤', '赤味噌', '醇香酱油'];
export const TOPPINGS = ['溏心蛋', '叉烧肉', '香菇'];
export const RECIPES = [
  { name: '月见白汤', broth: 0, topping: 0, tag: '浓郁 / 温柔', color: '#e5b35d' },
  { name: '赤焰叉烧', broth: 1, topping: 1, tag: '醇厚 / 热烈', color: '#c46749' },
  { name: '山野酱油', broth: 2, topping: 2, tag: '鲜香 / 清爽', color: '#778568' },
  { name: '味噌月见', broth: 1, topping: 0, tag: '醇厚 / 柔软', color: '#c46749' },
  { name: '白汤叉烧', broth: 0, topping: 1, tag: '浓郁 / 满足', color: '#e5b35d' },
  { name: '香菇白汤', broth: 0, topping: 2, tag: '鲜香 / 温暖', color: '#778568' },
];
export function newGame(chefId = 'blue', random = Math.random) {
  const chef = CHEFS.find(c => c.id === chefId) || CHEFS[0];
  const game = { chef, random, status: 'playing', remaining: 90, score: 0, served: 0, mistakes: 0, combo: 0, bestCombo: 0, perfect: 0, orders: [], orderTime: 0, bowl: {}, result: null };
  game.orders = Array.from({ length: 3 }, () => nextRecipe(game));
  resetBowl(game);
  return game;
}
function nextRecipe(game) { return RECIPES[Math.min(RECIPES.length - 1, Math.floor(game.random() * RECIPES.length))]; }
export function resetBowl(game) { game.bowl = { broth: null, topping: null, noodles: 'empty', cookTime: 0 }; }
function nextOrder(game) { game.orders.shift(); game.orders.push(nextRecipe(game)); game.orderTime = 0; resetBowl(game); }
function finish(game, reason) { game.status = 'finished'; game.result = reason; }
export function action(game, type, value) {
  if (game.status !== 'playing') return null;
  if (type === 'broth' || type === 'topping') {
    if (!Number.isInteger(value) || value < 0 || value > 2) return null;
    game.bowl[type] = value; return { kind: 'select' };
  }
  if (type === 'noodles') {
    if (game.bowl.noodles === 'cooking') {
      game.bowl.noodles = game.bowl.cookTime >= game.chef.min && game.bowl.cookTime <= game.chef.max ? 'perfect' : 'ready';
      return { kind: game.bowl.noodles };
    }
    game.bowl.noodles = 'cooking'; game.bowl.cookTime = 0; return { kind: 'cooking' };
  }
  if (type === 'clear') { resetBowl(game); return { kind: 'clear' }; }
  if (type !== 'serve') return null;
  if (game.bowl.broth === null || game.bowl.topping === null || !['perfect', 'ready', 'burnt'].includes(game.bowl.noodles)) return { kind: 'incomplete' };
  const recipe = game.orders[0];
  const correct = game.bowl.broth === recipe.broth && game.bowl.topping === recipe.topping && game.bowl.noodles !== 'burnt';
  let event;
  if (correct) {
    game.served++; game.combo++; game.bestCombo = Math.max(game.bestCombo, game.combo);
    const perfect = game.bowl.noodles === 'perfect';
    if (perfect) game.perfect++;
    const points = Math.round((100 + (perfect ? 50 : 0) + Math.min(game.combo - 1, 5) * 15) * game.chef.bonus);
    game.score += points; event = { kind: perfect ? 'success-perfect' : 'success', points };
  } else { game.mistakes++; game.combo = 0; event = { kind: 'wrong' }; }
  nextOrder(game);
  if (game.served >= 6) finish(game, 'win');
  else if (game.mistakes >= 3) finish(game, 'mistakes');
  return event;
}
export function tick(game, elapsed) {
  if (game.status !== 'playing' || !Number.isFinite(elapsed) || elapsed <= 0) return null;
  const dt = Math.min(elapsed, game.remaining);
  game.remaining = Math.max(0, game.remaining - dt);
  game.orderTime += dt;
  if (game.bowl.noodles === 'cooking') {
    game.bowl.cookTime = Math.min(4, game.bowl.cookTime + dt * (game.bowl.cookRate || 1));
    if (game.bowl.cookTime >= 4) game.bowl.noodles = 'burnt';
  }
  let event = null;
  if (game.orderTime >= game.chef.patience) { game.mistakes++; game.combo = 0; nextOrder(game); event = { kind: 'timeout' }; }
  if (game.mistakes >= 3) finish(game, 'mistakes');
  else if (game.remaining <= 0) finish(game, 'time');
  return event;
}
export function pause(game) { if (game.status === 'playing') game.status = 'paused'; else if (game.status === 'paused') game.status = 'playing'; }
