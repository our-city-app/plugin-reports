import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Action } from '@ngrx/store';
import { TranslateService } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ErrorService {

  constructor(private translate: TranslateService) {
  }

  getMessage(error: any): string {
    if (error instanceof HttpErrorResponse) {
      if (error.error && error.error.error) {
        return error.error.error;
      }
    }
    if (error instanceof Error) {
      console.error(error);
    }
    return this.translate.instant('r.err_unknown');
  }

  fromAction(action: any, error: any): Observable<Action> {
    const message = this.getMessage(error);
    return of(new (action as any)(message));
  }
}
