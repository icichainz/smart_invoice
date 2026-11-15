import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Plus, Edit, MoreHorizontal, Share2 } from 'lucide-react';
import { invoiceApi } from '../services/api';
import { Invoice } from '../types';
import { formatDate, formatCurrency, getErrorMessage } from '../utils';

const InvoiceList: React.FC = () => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [sharingId, setSharingId] = useState<number | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadInvoices();
  }, []);

  const loadInvoices = async () => {
    try {
      setLoading(true);
      const response = await invoiceApi.list();
      setInvoices(response.results);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (invoice: Invoice) => {
    navigate(`/invoices/${invoice.id}/edit`);
  };

  const handleShare = async (invoice: Invoice) => {
    setError('');
    setNotice('');
    try {
      setSharingId(invoice.id);
      let shareId = invoice.share_link_id;
      if (!shareId) {
        const response = await invoiceApi.generateShareLink(invoice.id);
        const updated = response.data;
        shareId = updated?.share_link_id ?? null;
        if (updated) {
          setInvoices((prev) => prev.map((inv) => (inv.id === updated.id ? updated : inv)));
        }
      }
      if (!shareId) {
        setError('Could not generate a share link.');
        return;
      }
      const url = `${window.location.origin}/share/${shareId}`;
      try {
        await navigator.clipboard.writeText(url);
        setNotice(`Share link copied to clipboard: ${url}`);
      } catch {
        // Clipboard API unavailable (e.g. insecure context) - let the user copy manually.
        window.prompt('Copy this share link:', url);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSharingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Invoices</h1>
        <Button onClick={() => navigate('/invoices/new')} className="flex items-center space-x-2">
          <Plus className="h-4 w-4" />
          <span>New Invoice</span>
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {notice && (
        <Alert>
          <AlertDescription>{notice}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Invoice List</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Invoice #</TableHead>
                <TableHead>Client</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Due Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Total</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoices.map((invoice) => (
                <TableRow key={invoice.id}>
                  <TableCell>#{invoice.id}</TableCell>
                  <TableCell>{invoice.client_name || 'No Client'}</TableCell>
                  <TableCell>{formatDate(invoice.created_at)}</TableCell>
                  <TableCell>{formatDate(invoice.due_date)}</TableCell>
                  <TableCell>
                    <span className="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800">
                      {invoice.status}
                    </span>
                  </TableCell>
                  <TableCell>{formatCurrency(invoice.total_amount_final)}</TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon" onClick={() => handleEdit(invoice)}>
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleShare(invoice)}
                      disabled={invoice.save_as_draft || sharingId === invoice.id}
                      title={invoice.save_as_draft ? 'Draft invoices cannot be shared' : 'Copy share link'}
                      aria-label="Share"
                    >
                      <Share2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

export default InvoiceList;