import React, { useState, useEffect } from 'react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Spinner } from '../components/ui/spinner';
import { profileApi } from '../services/api';
import { BusinessProfile } from '../types';
import { cn } from '../lib/utils';
import { getErrorMessage, isValidEmail } from '../utils';

type ProfileField = keyof BusinessProfile;
type FieldErrors = Partial<Record<ProfileField, string>>;

const EMPTY_PROFILE: BusinessProfile = {
  business_name: '',
  address: '',
  email: '',
  phone: '',
  tax_id: '',
  payment_instructions: '',
  footer_note: '',
};

// Same look as components/ui/input.tsx, sized for multi-line text.
const textareaClassName =
  'flex min-h-[96px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50';

// Pull DRF field errors ({ field: ["message"] }) out of an API error.
const extractFieldErrors = (err: any): FieldErrors => {
  const data = err?.response?.data;
  const errors: FieldErrors = {};
  if (data && typeof data === 'object') {
    (Object.keys(EMPTY_PROFILE) as ProfileField[]).forEach((field) => {
      const value = data[field];
      if (Array.isArray(value) && value.length > 0) {
        errors[field] = String(value[0]);
      } else if (typeof value === 'string') {
        errors[field] = value;
      }
    });
  }
  return errors;
};

const Settings: React.FC = () => {
  const [profile, setProfile] = useState<BusinessProfile>(EMPTY_PROFILE);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  useEffect(() => {
    const loadProfile = async () => {
      try {
        setLoading(true);
        const data = await profileApi.get();
        setProfile({ ...EMPTY_PROFILE, ...data });
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };
    loadProfile();
  }, []);

  const handleChange =
    (field: ProfileField) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const value = e.target.value;
      setProfile((prev) => ({ ...prev, [field]: value }));
      setSuccess('');
      if (fieldErrors[field]) {
        setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
      }
    };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const email = profile.email.trim();
    if (email && !isValidEmail(email)) {
      setFieldErrors({ email: 'Please enter a valid email address' });
      return;
    }

    const payload: BusinessProfile = {
      business_name: profile.business_name.trim(),
      address: profile.address.trim(),
      email,
      phone: profile.phone.trim(),
      tax_id: profile.tax_id.trim(),
      payment_instructions: profile.payment_instructions.trim(),
      footer_note: profile.footer_note.trim(),
    };

    try {
      setSaving(true);
      setFieldErrors({});
      const saved = await profileApi.update(payload);
      setProfile({ ...EMPTY_PROFILE, ...saved });
      setSuccess('Business details saved. They will appear on your invoice PDFs.');
    } catch (err) {
      const errors = extractFieldErrors(err);
      setFieldErrors(errors);
      setError(
        Object.keys(errors).length > 0
          ? 'Please fix the highlighted fields.'
          : getErrorMessage(err)
      );
    } finally {
      setSaving(false);
    }
  };

  const renderFieldError = (field: ProfileField) =>
    fieldErrors[field] ? (
      <p className="text-sm text-destructive">{fieldErrors[field]}</p>
    ) : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <Spinner size="lg" className="text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Business details</CardTitle>
          <CardDescription>
            These details appear as the sender on every invoice PDF, including PDFs your
            clients download from a share link. If no business name is set, your account
            name is used instead.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {success && (
            <Alert className="mb-4">
              <AlertDescription>{success}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="business_name">Business name</Label>
              <Input
                id="business_name"
                value={profile.business_name}
                onChange={handleChange('business_name')}
                maxLength={255}
                placeholder="Acme Design Studio"
              />
              {renderFieldError('business_name')}
            </div>

            <div className="space-y-2">
              <Label htmlFor="address">Address</Label>
              <textarea
                id="address"
                className={cn(textareaClassName, fieldErrors.address && 'border-destructive')}
                value={profile.address}
                onChange={handleChange('address')}
                rows={3}
                placeholder={'Street and number\nPostcode and city\nCountry'}
              />
              {renderFieldError('address')}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  className={cn(fieldErrors.email && 'border-destructive')}
                  value={profile.email}
                  onChange={handleChange('email')}
                  placeholder="billing@example.com"
                />
                {renderFieldError('email')}
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">Phone</Label>
                <Input
                  id="phone"
                  value={profile.phone}
                  onChange={handleChange('phone')}
                  maxLength={32}
                />
                {renderFieldError('phone')}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="tax_id">VAT / tax ID</Label>
              <Input
                id="tax_id"
                value={profile.tax_id}
                onChange={handleChange('tax_id')}
                maxLength={64}
              />
              {renderFieldError('tax_id')}
            </div>

            <div className="space-y-2">
              <Label htmlFor="payment_instructions">Payment instructions</Label>
              <textarea
                id="payment_instructions"
                className={cn(
                  textareaClassName,
                  fieldErrors.payment_instructions && 'border-destructive'
                )}
                value={profile.payment_instructions}
                onChange={handleChange('payment_instructions')}
                rows={4}
                placeholder="Bank name, account holder, IBAN / account number, reference to use..."
              />
              <p className="text-sm text-muted-foreground">
                Printed below the invoice totals.
              </p>
              {renderFieldError('payment_instructions')}
            </div>

            <div className="space-y-2">
              <Label htmlFor="footer_note">Footer note</Label>
              <Input
                id="footer_note"
                value={profile.footer_note}
                onChange={handleChange('footer_note')}
                maxLength={255}
                placeholder="Thank you for your business!"
              />
              {renderFieldError('footer_note')}
            </div>

            <Button type="submit" disabled={saving} className="flex items-center space-x-2">
              {saving && <Spinner size="sm" />}
              <span>{saving ? 'Saving...' : 'Save'}</span>
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default Settings;
