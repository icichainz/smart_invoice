import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Spinner } from '../components/ui/spinner';
import { Download } from 'lucide-react';
import { publicInvoiceApi } from '../services/api';
import { PublicInvoice } from '../types';
import { formatDate, formatCurrency, downloadBlob, getErrorMessage } from '../utils';

const SharedInvoice: React.FC = () => {
  const { shareId } = useParams<{ shareId: string }>();
  const [invoice, setInvoice] = useState<PublicInvoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!shareId) {
      setError('Invalid share link.');
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError('');

    publicInvoiceApi
      .get(shareId)
      .then((data) => {
        if (!cancelled) setInvoice(data);
      })
      .catch((err: any) => {
        if (cancelled) return;
        if (err.response?.status === 404) {
          setError('This invoice link is invalid or is no longer available.');
        } else {
          setError(getErrorMessage(err));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [shareId]);

  const handleDownload = async () => {
    if (!shareId || !invoice) return;
    try {
      setDownloading(true);
      const blob = await publicInvoiceApi.downloadPdf(shareId);
      downloadBlob(blob, `invoice_${invoice.id}.pdf`);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Spinner size="lg" className="text-muted-foreground" />
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="w-full max-w-md">
          <Alert variant="destructive">
            <AlertDescription>{error || 'Invoice not found.'}</AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Invoice #{invoice.id}</h1>
          <Button onClick={handleDownload} disabled={downloading} className="flex items-center space-x-2">
            {downloading ? <Spinner size="sm" /> : <Download className="h-4 w-4" />}
            <span>Download PDF</span>
          </Button>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <div className="text-sm text-muted-foreground">Billed to</div>
                <div className="font-medium">{invoice.client_name || 'No Client'}</div>
                {invoice.client_email && (
                  <div className="text-sm text-muted-foreground">{invoice.client_email}</div>
                )}
              </div>
              <div className="space-y-1 sm:text-right">
                <div>
                  <span className="text-sm text-muted-foreground">Issued: </span>
                  {formatDate(invoice.created_at)}
                </div>
                {invoice.due_date && (
                  <div>
                    <span className="text-sm text-muted-foreground">Due: </span>
                    {formatDate(invoice.due_date)}
                  </div>
                )}
                <div>
                  <span className="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800">
                    {invoice.status === 'paid' ? 'Paid' : 'Unpaid'}
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Items</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Item</TableHead>
                  <TableHead className="text-right">Qty</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoice.items.map((item, index) => (
                  <TableRow key={index}>
                    <TableCell>
                      <div className="font-medium">{item.title}</div>
                      {item.description && (
                        <div className="text-sm text-muted-foreground">{item.description}</div>
                      )}
                    </TableCell>
                    <TableCell className="text-right">{item.quantity}</TableCell>
                    <TableCell className="text-right">{formatCurrency(item.amount)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(item.total_amount)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <div className="mt-6 ml-auto w-full max-w-xs space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Subtotal</span>
                <span>{formatCurrency(invoice.total_amount)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">VAT ({invoice.vat_rate}%)</span>
                <span>{formatCurrency(invoice.vat_rate_amount)}</span>
              </div>
              <div className="flex justify-between border-t pt-2 font-semibold">
                <span>Total</span>
                <span>{formatCurrency(invoice.total_amount_final)}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default SharedInvoice;
