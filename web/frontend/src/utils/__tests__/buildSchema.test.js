import { buildSchemaFromCategories } from '../buildSchema';

describe('buildSchemaFromCategories Utility', () => {
  test('builds basic schema', () => {
    const categories = [{
      key: 'basic',
      label: 'Basic',
      fields: [
        { path: 'name', label: 'Name', type: 'string' },
        { path: 'age', label: 'Age', type: 'number' }
      ]
    }];

    const schema = buildSchemaFromCategories(categories);

    expect(schema).toEqual({
      type: 'object',
      additionalProperties: true,
      properties: {
        name: { type: 'string' },
        age: { type: 'number' }
      }
    });
  });

  test('builds nested schema', () => {
    const categories = [{
      key: 'user',
      label: 'User',
      fields: [
        { path: 'user.name', label: 'Name', type: 'string' },
        { path: 'user.address.street', label: 'Street', type: 'string' },
        { path: 'user.address.city', label: 'City', type: 'string' }
      ]
    }];

    const schema = buildSchemaFromCategories(categories);

    expect(schema.properties.user.properties.address.properties.street).toEqual({
      type: 'string'
    });
  });

  test('builds schema with validation rules', () => {
    const categories = [{
      key: 'validation',
      label: 'Validation',
      fields: [
        { path: 'age', label: 'Age', type: 'number', min: 0, max: 120 },
        { path: 'email', label: 'Email', type: 'string' }
      ]
    }];

    const schema = buildSchemaFromCategories(categories);

    expect(schema.properties.age).toEqual({
      type: 'number',
      minimum: 0,
      maximum: 120
    });
  });

  test('builds schema with enums', () => {
    const categories = [{
      key: 'enums',
      label: 'Enums',
      fields: [
        { path: 'role', label: 'Role', type: 'enum', options: ['admin', 'user', 'guest'] }
      ]
    }];

    const schema = buildSchemaFromCategories(categories);

    expect(schema.properties.role).toEqual({
      type: 'string',
      enum: ['admin', 'user', 'guest']
    });
  });

  test('builds schema with booleans', () => {
    const categories = [{
      key: 'booleans',
      label: 'Booleans',
      fields: [
        { path: 'isActive', label: 'Is Active', type: 'boolean' }
      ]
    }];

    const schema = buildSchemaFromCategories(categories);

    expect(schema.properties.isActive).toEqual({
      type: 'boolean'
    });
  });
});