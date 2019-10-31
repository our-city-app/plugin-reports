import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { Actions, Effect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { catchError, debounceTime, map, switchMap, tap } from 'rxjs/operators';
import { ErrorService } from './error.service';
import * as actions from './reports.actions';
import { ReportsActions, ReportsActionTypes } from './reports.actions';
import { ReportsService } from './reports.service';
import { IReportsState } from './reports.state';

@Injectable({ providedIn: 'root' })
export class ReportsEffects {

  @Effect() listSettings$ = this.actions$.pipe(
    ofType<actions.ListSettingsAction>(ReportsActionTypes.LIST_SETTINGS),
    switchMap(() => this.settingsService.listSettings().pipe(
      map(result => new actions.ListSettingsCompleteAction(result)),
      catchError(error => this.errorService.fromAction(actions.ListSettingsFailedAction, error)),
    )));

  @Effect() getSettings$ = this.actions$.pipe(
    ofType<actions.GetSettingsAction>(ReportsActionTypes.GET_SETTINGS),
    switchMap(action => this.settingsService.getSettings(action.payload.id).pipe(
      map(result => new actions.GetSettingsCompleteAction(result)),
      catchError(error => this.errorService.fromAction(actions.GetSettingsFailedAction, error)),
    )));

  @Effect() createSettings$ = this.actions$.pipe(
    ofType<actions.CreateSettingsAction>(ReportsActionTypes.CREATE_SETTINGS),
    switchMap(action => this.settingsService.createSettings(action.payload).pipe(
      map(result => new actions.CreateSettingsCompleteAction(result)),
      tap(result => {
        this.router.navigate(['/integrations', result.payload.id]);
      }),
      catchError(error => this.errorService.fromAction(actions.CreateSettingsFailedAction, error)),
    )));

  @Effect() updateSettings$ = this.actions$.pipe(
    ofType<actions.UpdateSettingsAction>(ReportsActionTypes.UPDATE_SETTINGS),
    switchMap(action => this.settingsService.saveSettings(action.payload.id as number, action.payload).pipe(
      map(result => new actions.UpdateSettingsCompleteAction(result)),
      tap(result => {
        this.router.navigate(['/integrations', result.payload.id]);
      }),
      catchError(error => this.errorService.fromAction(actions.UpdateSettingsFailedAction, error)),
    )));

  @Effect() getTopdeskData$ = this.actions$.pipe(
    ofType<actions.GetTopdeskDataAction>(ReportsActionTypes.GET_TOPDESK_DATA),
    debounceTime(500),
    switchMap(action => this.settingsService.getTopdeskData(action.payload).pipe(
      map(result => new actions.GetTopdeskDataCompleteAction(result)),
      catchError(error => this.errorService.fromAction(actions.GetTopdeskDataFailedAction, error)),
    )));

  constructor(private actions$: Actions<ReportsActions>,
              private store: Store<IReportsState>,
              private router: Router,
              private errorService: ErrorService,
              private settingsService: ReportsService) {
  }
}
