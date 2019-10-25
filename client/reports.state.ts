import { createFeatureSelector, createSelector } from '@ngrx/store';
import { CallStateType, initialStateResult, ResultState } from '../../framework/client/rpc';
import { IntegrationList, IntegrationSettings, TopdeskData } from './interfaces';

export interface IReportsState {
  integrations: ResultState<IntegrationList>;
  settings: ResultState<IntegrationSettings>;
  topdeskData: ResultState<TopdeskData>;
}

export const initialReportsState: IReportsState = {
  integrations: initialStateResult,
  settings: initialStateResult,
  topdeskData: initialStateResult,
};


export const pluginSelector = createFeatureSelector<IReportsState>('reports');

export const listIntegrations = createSelector(pluginSelector, s =>
  s.integrations.state === CallStateType.SUCCESS ? s.integrations.result : []);
export const getSettings = createSelector(pluginSelector, s => s.settings.result);
export const getTopdeskData = createSelector(pluginSelector, s => s.topdeskData.result);
