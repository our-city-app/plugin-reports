import { Action } from '@ngrx/store';
import { IntegrationSettings, TopdeskData, TopdeskSettings } from './interfaces';

export const enum ReportsActionTypes {
  LIST_SETTINGS = '[Reports] List settings',
  LIST_SETTINGS_COMPLETE = '[Reports] List settings complete',
  LIST_SETTINGS_FAILED = '[Reports] List settings failed',
  GET_SETTINGS = '[Reports] get settings',
  GET_SETTINGS_COMPLETE = '[Reports] get settings complete',
  GET_SETTINGS_FAILED = '[Reports] get settings failed',
  UPDATE_SETTINGS = '[Reports] update settings',
  UPDATE_SETTINGS_COMPLETE = '[Reports] update settings complete',
  UPDATE_SETTINGS_FAILED = '[Reports] update settings failed',
  GET_TOPDESK_DATA = '[Reports] get topdesk data',
  GET_TOPDESK_DATA_COMPLETE = '[Reports] get topdesk data complete',
  GET_TOPDESK_DATA_FAILED = '[Reports] get topdesk data failed',
}

export class ListSettingsAction implements Action {
  readonly type = ReportsActionTypes.LIST_SETTINGS;
}

export class ListSettingsCompleteAction implements Action {
  readonly type = ReportsActionTypes.LIST_SETTINGS_COMPLETE;

  constructor(public payload: IntegrationSettings[]) {
  }
}

export class ListSettingsFailedAction implements Action {
  readonly type = ReportsActionTypes.LIST_SETTINGS_FAILED;

  constructor(public payload: string) {
  }
}

export class GetSettingsAction implements Action {
  readonly type = ReportsActionTypes.GET_SETTINGS;

  constructor(public sik: string) {
  }
}

export class GetSettingsCompleteAction implements Action {
  readonly type = ReportsActionTypes.GET_SETTINGS_COMPLETE;

  constructor(public payload: IntegrationSettings) {
  }
}

export class GetSettingsFailedAction implements Action {
  readonly type = ReportsActionTypes.GET_SETTINGS_FAILED;

  constructor(public payload: string) {
  }
}

export class UpdateSettingsAction implements Action {
  readonly type = ReportsActionTypes.UPDATE_SETTINGS;

  constructor(public payload: IntegrationSettings) {
  }
}

export class UpdateSettingsCompleteAction implements Action {
  readonly type = ReportsActionTypes.UPDATE_SETTINGS_COMPLETE;

  constructor(public payload: IntegrationSettings) {
  }
}

export class UpdateSettingsFailedAction implements Action {
  readonly type = ReportsActionTypes.UPDATE_SETTINGS_FAILED;

  constructor(public payload: string) {
  }
}

export class GetTopdeskDataAction implements Action {
  readonly type = ReportsActionTypes.GET_TOPDESK_DATA;

  constructor(public payload: TopdeskSettings) {
  }
}

export class GetTopdeskDataCompleteAction implements Action {
  readonly type = ReportsActionTypes.GET_TOPDESK_DATA_COMPLETE;

  constructor(public payload: TopdeskData) {
  }
}

export class GetTopdeskDataFailedAction implements Action {
  readonly type = ReportsActionTypes.GET_TOPDESK_DATA_FAILED;

  constructor(public payload: string) {
  }
}

export type ReportsActions
  = ListSettingsAction
  | ListSettingsCompleteAction
  | ListSettingsFailedAction
  | GetSettingsAction
  | GetSettingsCompleteAction
  | GetSettingsFailedAction
  | UpdateSettingsAction
  | UpdateSettingsCompleteAction
  | UpdateSettingsFailedAction
  | GetTopdeskDataAction
  | GetTopdeskDataCompleteAction
  | GetTopdeskDataFailedAction;
