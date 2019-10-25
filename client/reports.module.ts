import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialogModule } from '@angular/material/dialog';
import { MAT_FORM_FIELD_DEFAULT_OPTIONS } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterModule } from '@angular/router';
import { EffectsModule } from '@ngrx/effects';
import { Store, StoreModule } from '@ngrx/store';
import { MetaGuard } from '@ngx-meta/core';
import { TranslateModule } from '@ngx-translate/core';
import { Route } from '../../framework/client/app.routes';
import { AddRoutesAction } from '../../framework/client/nav/sidebar/actions';
import { IAppState } from '../../framework/client/ngrx';
import { ThreePSettingsComponent } from './components/3p-settings/3p-settings.component';
import { TopdeskFieldMappingComponent } from './components/field-mapping/topdesk-field-mapping.component';
import { IntegrationSettingsComponent } from './components/integration-settings/integration-settings.component';
import { TopdeskSettingsComponent } from './components/topdesk-settings/topdesk-settings.component';
import { CreateIntegrationPageComponent } from './pages/create-integration-page/create-integration-page.component';
import { IntegrationSettingsPageComponent } from './pages/integration-settings-page.component';
import { SettingsListPageComponent } from './pages/settings-list-page/settings-list-page.component';
import { ReportsEffects } from './reports.effect';
import { reportsReducer } from './reports.reducer';

const routes: Route[] = [
  { path: '', redirectTo: 'integrations', pathMatch: 'full' },
  {
    path: 'integrations',
    canActivate: [MetaGuard],
    component: SettingsListPageComponent,
    data: {
      id: 'integrations',
      description: 'r.integrations',
      icon: 'extension',
      label: 'r.integrations',
      meta: { title: 'r.integrations' },
    },
  }, {
    path: 'integrations/create',
    canActivate: [MetaGuard],
    component: CreateIntegrationPageComponent,
    data: { meta: { title: 'r.settings' } },
  }, {
    path: 'integrations/:sik',
    canActivate: [MetaGuard],
    component: IntegrationSettingsPageComponent,
    data: { meta: { title: 'r.settings' } },
  }];

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    HttpClientModule,
    RouterModule.forChild(routes),
    StoreModule.forFeature('reports', reportsReducer),
    EffectsModule.forFeature([ReportsEffects]),
    TranslateModule,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    MatInputModule,
    MatListModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatCheckboxModule,
    MatSlideToggleModule,
    MatToolbarModule,
  ],
  exports: [],
  declarations: [
    CreateIntegrationPageComponent,
    TopdeskSettingsComponent,
    SettingsListPageComponent,
    IntegrationSettingsPageComponent,
    TopdeskFieldMappingComponent,
    IntegrationSettingsComponent,
    ThreePSettingsComponent,
  ],
  providers: [
    {
      provide: MAT_FORM_FIELD_DEFAULT_OPTIONS,
      useValue: {
        appearance: 'standard',
      },
    }],
})
export class ReportsModule {
  constructor(private store: Store<IAppState>) {
    this.store.dispatch(new AddRoutesAction(routes));
  }
}
