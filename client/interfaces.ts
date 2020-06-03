export const enum PropertyName {
  CALL_TYPE = 'callType',
  CATEGORY = 'category',
  SUB_CATEGORY = 'subCategory',
  BRANCH = 'branch',
  ENTRY_TYPE = 'entryType',
  LOCATION = 'location',
  OPERATOR = 'operator',
  OPERATOR_GROUP = 'operatorGroup',
  OPTIONAL_FIELDS_1 = 'optionalFields1',
  OPTIONAL_FIELDS_2 = 'optionalFields2'
}

export const enum ValueProperty {
  TEXT_1 = 'text1',
  TEXT_2 = 'text2',
  TEXT_3 = 'text3',
  TEXT_4 = 'text4',
  TEXT_5 = 'text5',
}

export const enum FieldMappingType {
  TEXT = 1,
  GPS_SINGLE_FIELD = 2,
  GPS_URL = 3,
  FIXED_VALUE = 4
}

export interface FieldMapping {
  type: FieldMappingType,
  step_id: string | null;
  property: PropertyName;
  value_properties: ValueProperty[];
  default_value: string;
}

export interface NameId {
  id: string;
  name: string;
}

export interface SubCategory extends NameId {
  category: NameId;
}

export interface OperatorGroups {
  groupName: string;
  id: string;
  // many more properties but we don't care
}

export interface Operator {
  firstName: string;
  surName: string;
  loginName: string;
  id: string;
}

export interface TopdeskData {
  branches: NameId[];
  categories: NameId[];
  subCategories: SubCategory[];
  callTypes: NameId[];
  entryTypes: NameId[];
  operators: Operator[];
  operatorGroups: OperatorGroups[];
}

export enum IntegrationProvider {
  TOPDESK = 'topdesk',
  THREE_P = '3p',
  GREEN_VALLEY = 'green_valley',
}

export interface TopdeskSettings {
  provider: IntegrationProvider.TOPDESK;
  api_url: string | null;
  username: string | null;
  password: string | null;
  caller_branch_id: string | null;
  call_type_id: string | null;
  category_id: string | null;
  sub_category_id: string | null;
  branch_id: string | null;
  entry_type_id: string | null;
  operator_id: string | null;
  operator_group_id: string | null;
  unregistered_users: boolean;
  field_mapping: FieldMapping[];
}

export interface ThreePSettings {
  provider: IntegrationProvider.THREE_P;
  gcs_bucket_name: string;
}

export interface GreenValleySettings {
  provider: IntegrationProvider.GREEN_VALLEY;
  username: string;
  password: string;
  topic: string;
  proxy_id: string;
  base_url: string;
  realm: string;
  gateway_client_id: string;
  gateway_client_secret: string;
}

export type IntegrationSettingsData = TopdeskSettings | ThreePSettings | GreenValleySettings;

export type IntegrationList = { id: number; name: string }[];

export interface IntegrationSettings {
  id?: number;
  name: string;
  app_id: string;
  sik: string;
  consumer_id: string;
  rogerthat_api_key: string;
  data: IntegrationSettingsData;
}
