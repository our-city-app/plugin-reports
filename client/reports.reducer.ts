import { stateError, stateLoading, stateSuccess } from '../../framework/client/rpc';
import { ReportsActions, ReportsActionTypes } from './reports.actions';
import { initialReportsState, IReportsState } from './reports.state';


export function reportsReducer(state: IReportsState = initialReportsState, action: ReportsActions): IReportsState {
  switch (action.type) {
    case ReportsActionTypes.LIST_SETTINGS:
      return {
        ...state,
        integrations: stateLoading(state.integrations.result),
      };
    case ReportsActionTypes.LIST_SETTINGS_COMPLETE:
      return {
        ...state,
        integrations: stateSuccess(action.payload),
      };
    case ReportsActionTypes.LIST_SETTINGS_FAILED:
      return {
        ...state,
        integrations: stateError(action.payload, state.integrations.result),
      };
    case ReportsActionTypes.GET_SETTINGS:
      return {
        ...state,
        settings: stateLoading(state.settings.result),
      };
    case ReportsActionTypes.GET_SETTINGS_COMPLETE:
      return {
        ...state,
        settings: stateSuccess(action.payload),
      };
    case ReportsActionTypes.GET_SETTINGS_FAILED:
      return {
        ...state,
        settings: stateError(action.payload, state.settings.result),
      };
    case ReportsActionTypes.GET_TOPDESK_DATA:
      return {
        ...state,
        topdeskData: stateLoading(state.topdeskData.result),
      };
    case ReportsActionTypes.GET_TOPDESK_DATA_COMPLETE:
      return {
        ...state,
        topdeskData: stateSuccess(action.payload),
      };
    case ReportsActionTypes.GET_TOPDESK_DATA_FAILED:
      return {
        ...state,
        topdeskData: stateError(action.payload, state.topdeskData.result),
      };
    default:
      return state;
  }
}
