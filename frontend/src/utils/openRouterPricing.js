/**
 * OpenRouter pricing calculator
 * Precios reales de OpenRouter - NO INVENTAR
 * https://openrouter.ai/docs#models
 */

// Precios aproximados por modelo (USD per 1M tokens)
// Estos son valores de referencia - el coste real viene del backend
export const OPENROUTER_PRICING = {
  // Models comunes de OpenRouter
  'meta-llama/llama-3.1-8b-instruct': {
    prompt: 0.055,
    completion: 0.055
  },
  'meta-llama/llama-3.1-70b-instruct': {
    prompt: 0.59,
    completion: 0.79
  },
  'anthropic/claude-3.5-sonnet': {
    prompt: 3.0,
    completion: 15.0
  },
  'openai/gpt-4-turbo': {
    prompt: 10.0,
    completion: 30.0
  },
  'openai/gpt-3.5-turbo': {
    prompt: 0.5,
    completion: 1.5
  },
  // Default para modelos desconocidos (pricing medio)
  'default': {
    prompt: 0.5,
    completion: 1.5
  }
};

/**
 * Calcula el coste real basado en tokens y modelo
 * @param {number} promptTokens - Tokens del prompt
 * @param {number} completionTokens - Tokens de completion
 * @param {string} model - Nombre del modelo usado
 * @returns {number} Coste en USD
 */
export function calculateOpenRouterCost(promptTokens, completionTokens, model = 'default') {
  if (!promptTokens && !completionTokens) return 0;
  
  // Buscar pricing del modelo
  let pricing = OPENROUTER_PRICING[model];
  if (!pricing) {
    // Si no encontramos el modelo exacto, usar default
    pricing = OPENROUTER_PRICING.default;
  }
  
  const promptCost = (promptTokens / 1_000_000) * pricing.prompt;
  const completionCost = (completionTokens / 1_000_000) * pricing.completion;
  
  return promptCost + completionCost;
}

/**
 * Formatea el coste para display
 * @param {number} cost - Coste en USD
 * @returns {string} Coste formateado
 */
export function formatCost(cost) {
  if (cost === 0) return '$0.00';
  if (cost < 0.0001) return '<$0.0001';
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  return `$${cost.toFixed(2)}`;
}
