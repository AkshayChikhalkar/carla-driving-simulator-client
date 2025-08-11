// Build a very permissive JSON Schema from settings categories
// Supports: type, enum, min, max

export function buildSchemaFromCategories(categories) {
  const schema = {
    type: 'object',
    additionalProperties: true,
    properties: {},
  };

  for (const cat of categories) {
    for (const field of cat.fields) {
      const path = field.path.split('.');
      let node = schema;
      for (let i = 0; i < path.length; i++) {
        const key = path[i];
        if (!node.properties) node.properties = {};
        if (!node.properties[key]) {
          node.properties[key] = { type: 'object', additionalProperties: true, properties: {} };
        }
        if (i === path.length - 1) {
          // leaf
          const leaf = {};
          switch (field.type) {
            case 'number':
              leaf.type = 'number';
              if (typeof field.min === 'number') leaf.minimum = field.min;
              if (typeof field.max === 'number') leaf.maximum = field.max;
              break;
            case 'boolean':
              leaf.type = 'boolean';
              break;
            case 'enum':
              leaf.type = 'string';
              if (Array.isArray(field.options)) leaf.enum = field.options;
              break;
            default:
              leaf.type = 'string';
          }
          node.properties[key] = leaf;
        } else {
          node = node.properties[key];
        }
      }
    }
  }
  return schema;
}


